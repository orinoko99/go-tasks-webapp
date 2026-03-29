"""
Pydantic схемы для задач Go (SGF файлы).

Этот модуль содержит схемы валидации данных для:
- Представления ходов в задаче
- Начальной позиции задачи (камни, кто ходит)
- Дерева ходов и вариаций
- Метаданных SGF файла

Все схемы используют Pydantic v2 синтаксис.
"""

from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ТИПЫ
# =============================================================================

# Тип для цвета камня в Go
# B = чёрные (Black), W = белые (White)
Color = Literal["B", "W"]


# =============================================================================
# СХЕМЫ ДЛЯ ХОДОВ И ПОЗИЦИЙ
# =============================================================================

class TaskMove(BaseModel):
    """
    Схема хода в задаче.

    Представляет один ход в дереве игры:
    - Координаты хода (x, y) или None для паса
    - Цвет камня (B=чёрные, W=белые)
    - Комментарий к ходу (если есть)
    - Метка узла (если есть)
    - Аннотации (tesuji, bad move, и т.д.)
    """
    x: Optional[int] = Field(None, ge=0, le=18, description="Координата X хода (0-18)")
    y: Optional[int] = Field(None, ge=0, le=18, description="Координата Y хода (0-18)")
    color: Color = Field(..., description="Цвет камня: B (чёрные) или W (белые)")
    comment: Optional[str] = Field(None, description="Комментарий к ходу")
    label: Optional[str] = Field(None, description="Метка узла (например, 'Solution')")
    is_correct: Optional[bool] = Field(None, description="Является ли ход правильным решением")
    move_number: Optional[int] = Field(None, ge=1, description="Номер хода в последовательности")

    model_config = {"from_attributes": True}

    @property
    def is_pass(self) -> bool:
        """
        Проверяет, является ли ход пасом.
        
        Returns:
            bool: True если ход является пасом (координаты None)
        """
        return self.x is None and self.y is None

    @property
    def sgf_coords(self) -> Optional[str]:
        """
        Преобразует координаты обратно в SGF формат.
        
        Returns:
            Optional[str]: Координаты в формате SGF (напр. "aa", "dd") или None для паса
        """
        if self.x is None or self.y is None:
            return None
        # Преобразуем числа обратно в буквы (0=a, 1=b, ...)
        letters = "abcdefghijklmnopqrstuvwxyz"
        return f"{letters[self.x]}{letters[self.y]}"


class TaskPosition(BaseModel):
    """
    Схема начальной позиции задачи.

    Содержит информацию о расстановке камней на доске
    перед началом решения задачи:
    - Список координат чёрных камней
    - Список координат белых камней
    - Кто ходит первым (B или W)
    """
    black_stones: List[tuple[int, int]] = Field(
        default_factory=list,
        description="Список координат чёрных камней [(x1, y1), (x2, y2), ...]"
    )
    white_stones: List[tuple[int, int]] = Field(
        default_factory=list,
        description="Список координат белых камней [(x1, y1), (x2, y2), ...]"
    )
    next_color: Color = Field("B", description="Кто ходит следующим (B или W)")

    model_config = {"from_attributes": True}

    @field_validator('black_stones', 'white_stones')
    @classmethod
    def validate_stones(cls, v: List[tuple[int, int]]) -> List[tuple[int, int]]:
        """
        Валидация координат камней.
        
        Проверяет, что все координаты находятся в пределах доски (0-18).
        """
        for x, y in v:
            if not (0 <= x <= 18 and 0 <= y <= 18):
                raise ValueError(f"Координаты камня ({x}, {y}) вне пределов доски")
        return v

    @property
    def black_stones_sgf(self) -> List[str]:
        """
        Преобразует координаты чёрных камней в SGF формат.
        
        Returns:
            List[str]: Список координат в формате SGF
        """
        letters = "abcdefghijklmnopqrstuvwxyz"
        return [f"{letters[x]}{letters[y]}" for x, y in self.black_stones]

    @property
    def white_stones_sgf(self) -> List[str]:
        """
        Преобразует координаты белых камней в SGF формат.
        
        Returns:
            List[str]: Список координат в формате SGF
        """
        letters = "abcdefghijklmnopqrstuvwxyz"
        return [f"{letters[x]}{letters[y]}" for x, y in self.white_stones]


# =============================================================================
# СХЕМЫ ДЛЯ ДЕРЕВА ХОДОВ
# =============================================================================

class TaskNode(BaseModel):
    """
    Схема узла дерева ходов.

    Представляет один узел в дереве вариаций задачи:
    - Ход в текущем узле
    - Дочерние узлы (вариации продолжения)
    - Комментарий к узлу
    - Разметка (кружки, треугольники, и т.д.)
    """
    move: Optional[TaskMove] = Field(None, description="Ход в текущем узле")
    children: List['TaskNode'] = Field(default_factory=list, description="Дочерние узлы (вариации)")
    comment: Optional[str] = Field(None, description="Комментарий к позиции")
    labels: Dict[str, str] = Field(default_factory=dict, description="Разметка на доске {координата: метка}")
    is_correct_branch: Optional[bool] = Field(None, description="Является ли ветка правильным решением")

    model_config = {"from_attributes": True}


# Для рекурсивной схемы нужно обновить forward reference
TaskNode.model_rebuild()


class TaskTree(BaseModel):
    """
    Схема дерева ходов задачи.

    Содержит корневой узел дерева и предоставляет методы
    для навигации по дереву ходов.
    """
    root: TaskNode = Field(..., description="Корневой узел дерева ходов")
    total_nodes: int = Field(0, ge=0, description="Общее количество узлов в дереве")

    model_config = {"from_attributes": True}

    def count_nodes(self, node: Optional[TaskNode] = None) -> int:
        """
        Рекурсивно подсчитывает количество узлов в дереве.
        
        Args:
            node: Узел для подсчёта (если None, используется корень)
            
        Returns:
            int: Количество узлов в поддереве
        """
        if node is None:
            node = self.root
        
        count = 1  # Считаем текущий узел
        for child in node.children:
            count += self.count_nodes(child)
        
        return count


# =============================================================================
# СХЕМЫ ДЛЯ ЗАДАЧ И КОЛЛЕКЦИЙ
# =============================================================================

class SgfTask(BaseModel):
    """
    Схема задачи из SGF файла.

    Представляет одну задачу по Go с начальной позицией
    и деревом ходов:
    - Начальная позиция (расстановка камней)
    - Дерево ходов и вариаций
    - Метаданные (название, описание, сложность)
    """
    initial_position: TaskPosition = Field(..., description="Начальная позиция задачи")
    game_tree: TaskTree = Field(..., description="Дерево ходов и вариаций")
    title: Optional[str] = Field(None, description="Название задачи")
    description: Optional[str] = Field(None, description="Описание задачи")
    difficulty: Optional[str] = Field(None, description="Уровень сложности")
    collection_name: Optional[str] = Field(None, description="Название сборника задач")
    board_size: int = Field(19, ge=9, le=19, description="Размер доски (9, 13, или 19)")
    rule_set: Optional[str] = Field(None, description="Правила (Japanese, Chinese, и т.д.)")

    model_config = {"from_attributes": True}

    @property
    def has_solution(self) -> bool:
        """
        Проверяет, есть ли в задаче помеченное правильное решение.
        
        Returns:
            bool: True если есть ветка с is_correct_branch=True
        """
        return self._has_correct_branch(self.game_tree.root)

    def _has_correct_branch(self, node: TaskNode) -> bool:
        """Рекурсивная проверка наличия правильной ветки."""
        if node.is_correct_branch:
            return True
        for child in node.children:
            if self._has_correct_branch(child):
                return True
        return False

    @property
    def total_variations(self) -> int:
        """
        Подсчитывает общее количество вариаций в дереве.
        
        Returns:
            int: Количество листовых узлов (конечных позиций)
        """
        return self._count_leaves(self.game_tree.root)

    def _count_leaves(self, node: TaskNode) -> int:
        """Рекурсивный подсчёт листовых узлов."""
        if not node.children:
            return 1  # Листовой узел
        return sum(self._count_leaves(child) for child in node.children)


class SgfCollectionMetadata(BaseModel):
    """
    Схема метаданных коллекции SGF файлов.

    Содержит общую информацию о файле с задачами:
    - Название коллекции
    - Автор
    - Дата создания
    - Дополнительные свойства
    """
    collection_name: Optional[str] = Field(None, description="Название коллекции задач")
    author: Optional[str] = Field(None, description="Автор коллекции")
    created_date: Optional[str] = Field(None, description="Дата создания")
    application: Optional[str] = Field(None, description="Приложение, создавшее файл")
    encoding: Optional[str] = Field("UTF-8", description="Кодировка файла")
    extra_properties: Dict[str, Any] = Field(default_factory=dict, description="Дополнительные свойства")

    model_config = {"from_attributes": True}


class SgfCollection(BaseModel):
    """
    Схема коллекции задач из SGF файла.

    Представляет весь SGF файл с одной или несколькими задачами:
    - Список задач
    - Метаданные коллекции
    - Путь к файлу
    """
    tasks: List[SgfTask] = Field(..., description="Список задач в коллекции")
    metadata: SgfCollectionMetadata = Field(..., description="Метаданные коллекции")
    file_path: Optional[str] = Field(None, description="Путь к SGF файлу")
    total_tasks: int = Field(0, ge=0, description="Общее количество задач")

    model_config = {"from_attributes": True}

    @property
    def has_tasks(self) -> bool:
        """
        Проверяет, есть ли задачи в коллекции.
        
        Returns:
            bool: True если коллекция содержит задачи
        """
        return len(self.tasks) > 0

    @property
    def total_variations(self) -> int:
        """
        Подсчитывает общее количество вариаций во всех задачах.
        
        Returns:
            int: Сумма вариаций всех задач
        """
        return sum(task.total_variations for task in self.tasks)


# =============================================================================
# СХЕМЫ ДЛЯ API ОТВЕТОВ
# =============================================================================

class TaskListResponse(BaseModel):
    """
    Схема ответа со списком задач.

    Используется API для возврата списка задач из сборника.
    """
    tasks: List[SgfTask] = Field(..., description="Список задач")
    total: int = Field(..., ge=0, description="Общее количество задач")
    collection_name: Optional[str] = Field(None, description="Название сборника")

    model_config = {"from_attributes": True}


class TaskResponse(BaseModel):
    """
    Схема ответа с одной задачей.

    Используется API для возврата конкретной задачи.
    """
    task: SgfTask = Field(..., description="Данные задачи")
    success: bool = Field(True, description="Статус ответа")

    model_config = {"from_attributes": True}


class MoveRequest(BaseModel):
    """
    Схема запроса хода.

    Используется клиентом для отправки хода на сервер.
    """
    x: int = Field(..., ge=0, le=18, description="Координата X хода")
    y: int = Field(..., ge=0, le=18, description="Координата Y хода")
    task_id: str = Field(..., description="Идентификатор задачи")

    model_config = {"from_attributes": True}


class MoveResponse(BaseModel):
    """
    Схема ответа на ход.

    Возвращает результат хода пользователя:
    - Правильный ли ход
    - Ответный ход компьютера (если есть)
    - Сообщение о результате
    """
    is_correct: bool = Field(..., description="Правильный ли ход")
    computer_move: Optional[TaskMove] = Field(None, description="Ответный ход компьютера")
    message: str = Field(..., description="Сообщение о результате")
    is_solved: bool = Field(False, description="Решена ли задача")
    game_over: bool = Field(False, description="Завершена ли игра")

    model_config = {"from_attributes": True}
