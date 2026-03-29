"""
SGF парсер для системы Go Problems Trainer.

Этот модуль содержит функции для парсинга SGF (Smart Game Format) файлов
с задачами по игре Go. SGF - стандартный формат для хранения записей игр
и задач по Го.

Функционал:
- Парсинг SGF файлов с одной или несколькими задачами
- Извлечение начальной позиции (расстановка камней AB/AW/PL)
- Построение дерева ходов с вариациями
- Преобразование координат (SGF буквы ↔ кортежи x,y)
- Извлечение метаданных (название, описание, сложность)

Формат SGF:
- Координаты: две буквы от 'aa' до 'ss' (для доски 19x19)
- 'a' = 0, 'b' = 1, ..., 's' = 18
- Первая буква = столбец (x), вторая = строка (y)
- (0, 0) = верхний левый угол

Пример SGF:
    (;GM[1]FF[4]SZ[19]
    ;AB[pd]AW[qd]PL[B]  ; начальная позиция
    ;B[pe]C[Правильный ход]  ; ход чёрных
    ;W[qe]  ; ответный ход белых
    )
"""

import re
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

from backend.schemas.task import (
    SgfCollection,
    SgfTask,
    SgfCollectionMetadata,
    TaskPosition,
    TaskMove,
    TaskNode,
    TaskTree,
    Color,
)


# =============================================================================
# КОНСТАНТЫ И ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

# Буквы для координат SGF (a=0, b=1, ..., s=18)
SGF_LETTERS = "abcdefghijklmnopqrstuvwxyz"

# Максимальный размер доски (19x19 = s)
MAX_BOARD_SIZE = 19


def sgf_coords_to_tuple(coord_str: str) -> Tuple[int, int]:
    """
    Преобразует SGF координаты (напр. "aa", "dd") в кортеж (x, y).

    SGF использует систему координат от верхнего левого угла:
    - Первая буква = столбец (x), 0 = левый край
    - Вторая буква = строка (y), 0 = верхний край

    Args:
        coord_str (str): Координаты в формате SGF (две буквы)
            Примеры: "aa" (верхний левый), "dd" (3, 3), "pd" (15, 3)

    Returns:
        Tuple[int, int]: Кортеж (x, y) где 0 <= x, y <= 18

    Raises:
        ValueError: Если координаты некорректны

    Example:
        >>> sgf_coords_to_tuple("aa")
        (0, 0)
        >>> sgf_coords_to_tuple("dd")
        (3, 3)
        >>> sgf_coords_to_tuple("pd")
        (15, 3)
    """
    if not coord_str or len(coord_str) != 2:
        raise ValueError(f"Некорректные SGF координаты: {coord_str}")

    x_char, y_char = coord_str.lower()

    if x_char not in SGF_LETTERS or y_char not in SGF_LETTERS:
        raise ValueError(f"Некорректные SGF координаты: {coord_str}")

    x = SGF_LETTERS.index(x_char)
    y = SGF_LETTERS.index(y_char)

    return (x, y)


def tuple_to_sgf_coords(x: int, y: int) -> str:
    """
    Преобразует кортеж (x, y) обратно в SGF координаты.

    Args:
        x (int): Координата X (столбец), 0 <= x <= 18
        y (int): Координата Y (строка), 0 <= y <= 18

    Returns:
        str: Координаты в формате SGF (две буквы)

    Raises:
        ValueError: Если координаты вне пределов доски

    Example:
        >>> tuple_to_sgf_coords(0, 0)
        'aa'
        >>> tuple_to_sgf_coords(3, 3)
        'dd'
        >>> tuple_to_sgf_coords(15, 3)
        'pd'
    """
    if not (0 <= x < MAX_BOARD_SIZE and 0 <= y < MAX_BOARD_SIZE):
        raise ValueError(f"Координаты ({x}, {y}) вне пределов доски")

    return f"{SGF_LETTERS[x]}{SGF_LETTERS[y]}"


def parse_sgf_property_value(value_str: str) -> str:
    """
    Парсит значение свойства SGF, обрабатывая экранированные символы.

    SGF использует экранирование:
    - \\] → ] (закрывающая квадратная скобка)
    - \\\\ → \\ (обратный слэш)
    - \n → перевод строки

    Args:
        value_str (str): Значение свойства из SGF файла

    Returns:
        str: Обработанное значение с расшифрованными символами

    Example:
        >>> parse_sgf_property_value("Hello\\]World")
        'Hello]World'
    """
    # Заменяем экранированные символы
    value_str = value_str.replace("\\\\", "\x00")  # Временно заменяем \\
    value_str = value_str.replace("\\]", "]")
    value_str = value_str.replace("\x00", "\\")  # Восстанавливаем \\
    value_str = value_str.replace("\\n", "\n")

    return value_str


# =============================================================================
# КЛАСС ДЛЯ ПАРСИНГА SGF
# =============================================================================

class SGFParser:
    """
    Парсер SGF файлов.

    Этот класс отвечает за:
    - Лексический анализ SGF содержимого
    - Построение дерева узлов из SGF структуры
    - Извлечение свойств и значений
    - Преобразование в схемы Pydantic
    """

    def __init__(self, content: str):
        """
        Инициализирует парсер SGF содержимым.

        Args:
            content (str): Содержимое SGF файла как строка
        """
        self.content = content
        self.pos = 0  # Текущая позиция в строке
        self.length = len(content)

    def parse(self) -> List[Dict[str, Any]]:
        """
        Парсит SGF содержимое и возвращает список деревьев игр.

        Returns:
            List[Dict[str, Any]]: Список словарей, представляющих деревья игр

        Raises:
            ValueError: Если SGF формат некорректен
        """
        self._skip_whitespace()

        # SGF файл должен начинаться с "text" или "("
        if self.pos < self.length and self.content[self.pos:self.pos + 4] == "text":
            self.pos += 4
            self._skip_whitespace()

        trees = []

        # Парсим коллекцию деревьев
        while self.pos < self.length:
            self._skip_whitespace()
            if self.pos >= self.length:
                break

            if self.content[self.pos] == '(':
                tree = self._parse_game_tree()
                trees.append(tree)
            else:
                break

        return trees

    def _skip_whitespace(self):
        """Пропускает пробельные символы."""
        while self.pos < self.length and self.content[self.pos] in ' \t\n\r':
            self.pos += 1

    def _parse_game_tree(self) -> Dict[str, Any]:
        """
        Парсит одно дерево игры.

        Формат: (;node_properties [вариации])

        Returns:
            Dict[str, Any]: Словарь с узлами дерева
        """
        if self.content[self.pos] != '(':
            raise ValueError(f"Ожидалось '(', получено '{self.content[self.pos]}'")

        self.pos += 1  # Пропускаем '('
        self._skip_whitespace()

        nodes = []

        # Парсим последовательность узлов
        while self.pos < self.length and self.content[self.pos] == ';':
            node = self._parse_node()
            nodes.append(node)
            self._skip_whitespace()

        # Парсим вариации (дочерние деревья)
        variations = []
        while self.pos < self.length and self.content[self.pos] == '(':
            variation = self._parse_game_tree()
            variations.append(variation)

        self._skip_whitespace()

        # Закрывающая скобка
        if self.pos < self.length and self.content[self.pos] == ')':
            self.pos += 1
        else:
            raise ValueError(f"Ожидалось ')', позиция {self.pos}")

        return {
            'nodes': nodes,
            'variations': variations
        }

    def _parse_node(self) -> Dict[str, Any]:
        """
        Парсит один узел игры.

        Формат: ;Property1[value1][value2]Property2[value]...

        Returns:
            Dict[str, Any]: Словарь со свойствами узла
        """
        if self.content[self.pos] != ';':
            raise ValueError(f"Ожидалось ';', получено '{self.content[self.pos]}'")

        self.pos += 1  # Пропускаем ';'
        properties = {}

        # Парсим свойства узла
        while self.pos < self.length:
            # Пропускаем пробелы и переносы строк перед свойством
            self._skip_whitespace()
            
            # Если встретился конец узла или дерева
            if self.pos >= self.length:
                break
                
            current_char = self.content[self.pos]
            if current_char in ');':
                break

            # Парсим свойство
            prop_id, prop_value = self._parse_property()
            
            # SGF позволяет несколько значений для одного свойства: AB[aa][ab][ac]
            # Собираем все значения для этого свойства
            all_values = [prop_value]
            current_prop_id = prop_id
            
            while self.pos < self.length:
                self._skip_whitespace()
                
                # Если следующее значение (ещё одна квадратная скобка)
                if self.pos < self.length and self.content[self.pos] == '[':
                    self.pos += 1  # Пропускаем '['
                    
                    # Находим закрывающую скобку
                    value_start = self.pos
                    while self.pos < self.length:
                        if self.content[self.pos] == '\\' and self.pos + 1 < self.length:
                            self.pos += 2
                        elif self.content[self.pos] == ']':
                            break
                        else:
                            self.pos += 1
                    
                    value_str = self.content[value_start:self.pos]
                    if self.pos < self.length:
                        self.pos += 1  # Пропускаем ']'
                    
                    value = parse_sgf_property_value(value_str)
                    all_values.append(value)
                else:
                    break
            
            # Сохраняем все значения свойства
            # Если несколько значений, объединяем их пробелом
            properties[current_prop_id] = ' '.join(all_values)

        return properties

    def _parse_property(self) -> Tuple[str, str]:
        """
        Парсит одно свойство узла.

        Формат: PropertyIdent[value]

        Returns:
            Tuple[str, str]: (идентификатор свойства, значение)
        """
        # Парсим идентификатор свойства (1-2 заглавные буквы)
        prop_id_start = self.pos
        while self.pos < self.length and self.content[self.pos].isupper():
            self.pos += 1

        prop_id = self.content[prop_id_start:self.pos]

        if not prop_id:
            raise ValueError(f"Ожидался идентификатор свойства, позиция {self.pos}")

        self._skip_whitespace()

        # Парсим значение в квадратных скобках
        if self.pos >= self.length or self.content[self.pos] != '[':
            # Свойство без значения (флаг)
            return prop_id, ""

        self.pos += 1  # Пропускаем '['

        # Находим закрывающую скобку, учитывая экранирование
        value_start = self.pos
        while self.pos < self.length:
            if self.content[self.pos] == '\\' and self.pos + 1 < self.length:
                self.pos += 2  # Пропускаем экранированный символ
            elif self.content[self.pos] == ']':
                break
            else:
                self.pos += 1

        value_str = self.content[value_start:self.pos]

        if self.pos < self.length:
            self.pos += 1  # Пропускаем ']'

        # Обрабатываем экранированные символы
        value = parse_sgf_property_value(value_str)

        return prop_id, value


# =============================================================================
# ФУНКЦИИ ВЫСОКОГО УРОВНЯ
# =============================================================================

def parse_sgf_file(file_path: str) -> SgfCollection:
    """
    Парсит SGF файл и возвращает коллекцию задач.

    Функция читает файл, парсит его содержимое и преобразует
    в структуру Pydantic схем.

    Args:
        file_path (str): Путь к SGF файлу

    Returns:
        SgfCollection: Коллекция задач из SGF файла

    Raises:
        FileNotFoundError: Если файл не найден
        ValueError: Если SGF формат некорректен

    Example:
        >>> collection = parse_sgf_file("problems/task.sgf")
        >>> print(f"Найдено задач: {collection.total_tasks}")
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"SGF файл не найден: {file_path}")

    # Читаем содержимое файла
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    return parse_sgf_content(content, str(path))


def parse_sgf_content(content: str, file_path: Optional[str] = None) -> SgfCollection:
    """
    Парсит SGF содержимое из строки.

    Args:
        content (str): Содержимое SGF файла
        file_path (Optional[str]): Путь к файлу (для метаданных)

    Returns:
        SgfCollection: Коллекция задач

    Example:
        >>> with open("task.sgf") as f:
        ...     collection = parse_sgf_content(f.read())
    """
    # Создаём парсер и парсим содержимое
    parser = SGFParser(content)
    trees = parser.parse()

    if not trees:
        # Возвращаем пустую коллекцию
        return SgfCollection(
            tasks=[],
            metadata=SgfCollectionMetadata(),
            file_path=file_path,
            total_tasks=0
        )

    # Извлекаем метаданные из первого дерева
    metadata = _extract_metadata(trees[0], file_path)

    # Преобразуем каждое дерево в задачу
    tasks = []
    for tree in trees:
        task = _tree_to_task(tree, metadata.collection_name)
        if task:
            tasks.append(task)

    return SgfCollection(
        tasks=tasks,
        metadata=metadata,
        file_path=file_path,
        total_tasks=len(tasks)
    )


def _extract_metadata(tree: Dict[str, Any], file_path: Optional[str] = None) -> SgfCollectionMetadata:
    """
    Извлекает метаданные из SGF дерева.

    Args:
        tree (Dict[str, Any]): SGF дерево
        file_path (Optional[str]): Путь к файлу

    Returns:
        SgfCollectionMetadata: Метаданные коллекции
    """
    properties = {}

    # Собираем свойства из всех узлов корня
    for node in tree.get('nodes', []):
        properties.update(node)

    # Извлекаем известные метаданные
    collection_name = properties.get('GN', '')  # Game Name
    author = properties.get('PW', '') or properties.get('PB', '')  # Player White/Black
    created_date = properties.get('DT', '')  # Date
    application = properties.get('AP', '')  # Application
    encoding = properties.get('CA', 'UTF-8')  # Encoding

    # Собираем дополнительные свойства
    extra = {}
    known_props = {'GN', 'PW', 'PB', 'DT', 'AP', 'CA', 'FF', 'GM', 'SZ', 'RU'}
    for key, value in properties.items():
        if key not in known_props and value:
            extra[key] = value

    return SgfCollectionMetadata(
        collection_name=collection_name or None,
        author=author or None,
        created_date=created_date or None,
        application=application or None,
        encoding=encoding,
        extra_properties=extra
    )


def _tree_to_task(tree: Dict[str, Any], collection_name: Optional[str] = None) -> Optional[SgfTask]:
    """
    Преобразует SGF дерево в задачу.

    Args:
        tree (Dict[str, Any]): SGF дерево
        collection_name (Optional[str]): Название коллекции

    Returns:
        Optional[SgfTask]: Задача или None если не удалось преобразовать
    """
    nodes = tree.get('nodes', [])

    if not nodes:
        return None

    # Находим узел с setup-свойствами (AB/AW/PL)
    setup_node_idx = 0
    for i, node in enumerate(nodes):
        if 'AB' in node or 'AW' in node or 'PL' in node:
            setup_node_idx = i
            break

    # Извлекаем начальную позицию
    initial_position = _extract_initial_position(nodes[setup_node_idx])

    # Извлекаем метаданные задачи
    all_properties = {}
    for node in nodes:
        all_properties.update(node)

    title = all_properties.get('GN', '')
    description = all_properties.get('C', '')

    # Определяем размер доски
    board_size_str = all_properties.get('SZ', '19')
    try:
        board_size = int(board_size_str)
    except ValueError:
        board_size = 19

    # Определяем правила
    rule_set = all_properties.get('RU', '')

    # Строим дерево ходов
    game_tree = _build_game_tree(nodes[setup_node_idx:], tree.get('variations', []))

    return SgfTask(
        initial_position=initial_position,
        game_tree=game_tree,
        title=title or None,
        description=description or None,
        collection_name=collection_name,
        board_size=board_size,
        rule_set=rule_set or None
    )


def _extract_initial_position(node: Dict[str, str]) -> TaskPosition:
    """
    Извлекает начальную позицию из узла setup.

    Args:
        node (Dict[str, str]): Узел с свойствами AB/AW/PL

    Returns:
        TaskPosition: Начальная позиция задачи
    """
    black_stones = []
    white_stones = []
    next_color: Color = "B"

    # Парсим чёрные камни (AB - Add Black)
    if 'AB' in node:
        ab_value = node['AB']
        # AB может содержать несколько координат через пробел или запятую
        coords = re.split(r'[\s,]+', ab_value)
        for coord in coords:
            coord = coord.strip()
            if coord:
                try:
                    black_stones.append(sgf_coords_to_tuple(coord))
                except ValueError:
                    pass  # Пропускаем некорректные координаты

    # Парсим белые камни (AW - Add White)
    if 'AW' in node:
        aw_value = node['AW']
        coords = re.split(r'[\s,]+', aw_value)
        for coord in coords:
            coord = coord.strip()
            if coord:
                try:
                    white_stones.append(sgf_coords_to_tuple(coord))
                except ValueError:
                    pass

    # Определяем, кто ходит следующим (PL - Player)
    if 'PL' in node:
        pl_value = node['PL'].upper()
        if pl_value == 'W':
            next_color = "W"
        else:
            next_color = "B"

    return TaskPosition(
        black_stones=black_stones,
        white_stones=white_stones,
        next_color=next_color
    )


def _build_game_tree(nodes: List[Dict[str, str]], variations: List[Dict[str, Any]]) -> TaskTree:
    """
    Строит дерево ходов из SGF узлов.

    Args:
        nodes (List[Dict[str, str]]): Список узлов
        variations (List[Dict[str, Any]]): Вариации дерева

    Returns:
        TaskTree: Дерево ходов задачи
    """
    if not nodes:
        return TaskTree(root=TaskNode(), total_nodes=0)

    # Создаём корневой узел (без хода, только комментарий)
    root = _node_to_task_node(nodes[0])

    # Строим цепочку ходов из последовательных узлов
    current = root
    for i in range(1, len(nodes)):
        child_node = _node_to_task_node(nodes[i])
        current.children.append(child_node)
        current = child_node

    # Добавляем вариации
    for variation in variations:
        var_tree = _build_game_tree(
            variation.get('nodes', []),
            variation.get('variations', [])
        )
        if var_tree.root.move or var_tree.root.comment:
            root.children.append(var_tree.root)

    # Подсчитываем общее количество узлов
    total_nodes = _count_tree_nodes(root)

    return TaskTree(root=root, total_nodes=total_nodes)


def _node_to_task_node(node: Dict[str, str]) -> TaskNode:
    """
    Преобразует SGF узел в TaskNode.

    Args:
        node (Dict[str, str]): SGF узел

    Returns:
        TaskNode: Узел дерева задач
    """
    move = None
    comment = None
    labels = {}
    is_correct_branch = None

    # Извлекаем ход (B или W)
    if 'B' in node:
        b_coord = node['B']
        if b_coord:  # Не пустой ход (не пасс)
            try:
                x, y = sgf_coords_to_tuple(b_coord)
                move = TaskMove(x=x, y=y, color="B")
            except ValueError:
                pass
        else:
            # Пасс
            move = TaskMove(x=None, y=None, color="B")

    elif 'W' in node:
        w_coord = node['W']
        if w_coord:
            try:
                x, y = sgf_coords_to_tuple(w_coord)
                move = TaskMove(x=x, y=y, color="W")
            except ValueError:
                pass
        else:
            move = TaskMove(x=None, y=None, color="W")

    # Извлекаем комментарий
    if 'C' in node:
        comment = node['C']

    # Извлекаем метку узла
    if 'N' in node:
        label_value = node['N']
        # Проверяем, является ли ветка правильной
        if 'solution' in label_value.lower() or 'correct' in label_value.lower() or 'right' in label_value.lower():
            is_correct_branch = True
        elif 'wrong' in label_value.lower() or 'fail' in label_value.lower() or 'bad' in label_value.lower():
            is_correct_branch = False

    # Извлекаем аннотации
    if 'TE' in node:  # Tesuji (хороший ход)
        is_correct_branch = True
    if 'BM' in node:  # Bad move (плохой ход)
        is_correct_branch = False

    # Извлекаем разметку (LB - Label)
    if 'LB' in node:
        # LB[dd:A][ee:B] - метки на точках
        lb_matches = re.findall(r'\[([a-s]{2}):([^\]]+)\]', node['LB'])
        for coord, label in lb_matches:
            labels[coord] = label

    # Извлекаем кружки (CR) и другие маркеры
    if 'CR' in node:
        cr_coords = re.findall(r'[a-s]{2}', node['CR'])
        for coord in cr_coords:
            if coord not in labels:
                labels[coord] = 'CR'

    return TaskNode(
        move=move,
        children=[],
        comment=comment,
        labels=labels,
        is_correct_branch=is_correct_branch
    )


def _count_tree_nodes(root: TaskNode) -> int:
    """
    Рекурсивно подсчитывает количество узлов в дереве.

    Args:
        root (TaskNode): Корневой узел

    Returns:
        int: Общее количество узлов
    """
    count = 1
    for child in root.children:
        count += _count_tree_nodes(child)
    return count


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ЗАДАЧ
# =============================================================================

def get_task_possible_moves(task: SgfTask, current_node: TaskNode) -> List[TaskMove]:
    """
    Возвращает список возможных ходов из текущей позиции.

    Args:
        task (SgfTask): Задача
        current_node (TaskNode): Текущий узел в дереве

    Returns:
        List[TaskMove]: Список возможных ходов
    """
    moves = []
    for child in current_node.children:
        if child.move:
            moves.append(child.move)
    return moves


def get_task_solution_path(task: SgfTask) -> List[TaskMove]:
    """
    Находит путь решения задачи (правильную ветку).

    Args:
        task (SgfTask): Задача

    Returns:
        List[TaskMove]: Список ходов, ведущих к решению
    """
    path = []
    _find_solution_path(task.game_tree.root, path)
    return path


def _find_solution_path(node: TaskNode, path: List[TaskMove]) -> bool:
    """
    Рекурсивно ищет путь решения.

    Returns:
        bool: True если решение найдено
    """
    if node.is_correct_branch:
        if node.move:
            path.append(node.move)
        return True

    for child in node.children:
        if _find_solution_path(child, path):
            if node.move:
                path.insert(0, node.move)
            return True

    return False
