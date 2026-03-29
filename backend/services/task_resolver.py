"""
Сервис проверки ходов и управления состоянием доски для системы Go Problems Trainer.

Этот модуль содержит логику для:
- Представления состояния доски (BoardState)
- Проверки корректности хода (валидация координат, занятость точки)
- Выполнения хода на доске (размещение камня)
- Проверки захвата камней (удаление захваченных групп)
- Определения состояния игры (подсчёт очков, определение победителя)

Правила Go, реализованные в этом модуле:
- Доска 19x19 (также поддерживаются 9x9 и 13x13)
- Чёрные ходят первыми
- Камни захватываются, когда у них не остаётся свободных точек (даме)
- Запрещён суицидальный ход (ход, который сразу приводит к захвату собственного камня)
- Правило ко (запрещено повторение позиции)

Пример использования:
    >>> resolver = TaskResolver(board_size=19)
    >>> resolver.make_move(3, 3, "B")  # Чёрные ставят камень на (3, 3)
    >>> resolver.get_liberties(3, 3)   # Получить количество даме
    4
    >>> resolver.is_captured(3, 3)     # Проверить, захвачен ли камень
    False
"""

from typing import Optional, List, Tuple, Set, Dict
from dataclasses import dataclass, field
from enum import Enum
from copy import deepcopy


# =============================================================================
# ТИПЫ И КОНСТАНТЫ
# =============================================================================

# Цвет камня: None = пусто, "B" = чёрные, "W" = белые
StoneColor = Optional[str]

# Координаты на доске
Coords = Tuple[int, int]


class GameState(Enum):
    """
    Состояние игры.
    
    ACTIVE - игра продолжается
    RESIGNED - один из игроков сдался
    SCORED - игра завершена, идёт подсчёт очков
    """
    ACTIVE = "active"
    RESIGNED = "resigned"
    SCORED = "scored"


# =============================================================================
# КЛАССЫ ДАННЫХ
# =============================================================================

@dataclass
class BoardState:
    """
    Состояние доски в текущий момент.
    
    Атрибуты:
        board (List[List[StoneColor]]): Двумерный массив доски
        board_size (int): Размер доски (9, 13, или 19)
        next_color (StoneColor): Чей сейчас ход
        captured_black (int): Количество захваченных чёрных камней
        captured_white (int): Количество захваченных белых камней
        last_move (Optional[Coords]): Последний сделанный ход
        previous_positions (Set[str]): История позиций для правила ко
        game_state (GameState): Состояние игры
    """
    board: List[List[StoneColor]]
    board_size: int = 19
    next_color: StoneColor = "B"
    captured_black: int = 0
    captured_white: int = 0
    last_move: Optional[Coords] = None
    previous_positions: Set[str] = field(default_factory=set)
    game_state: GameState = GameState.ACTIVE
    
    def copy(self) -> 'BoardState':
        """
        Создаёт глубокую копию состояния доски.
        
        Returns:
            BoardState: Копия текущего состояния
        """
        return BoardState(
            board=deepcopy(self.board),
            board_size=self.board_size,
            next_color=self.next_color,
            captured_black=self.captured_black,
            captured_white=self.captured_white,
            last_move=self.last_move,
            previous_positions=self.previous_positions.copy(),
            game_state=self.game_state
        )
    
    def get_position_hash(self) -> str:
        """
        Создаёт строковое представление позиции для правила ко.
        
        Returns:
            str: Уникальная строка, представляющая текущую позицию
        """
        return str(self.board)


# =============================================================================
# КЛАСС TASK RESOLVER
# =============================================================================

class TaskResolver:
    """
    Решатель задач для проверки ходов в игре Go.
    
    Этот класс предоставляет методы для:
    - Создания и инициализации доски
    - Проверки корректности хода
    - Выполнения хода на доске
    - Проверки захвата камней
    - Подсчёта даме (свободных точек)
    - Определения состояния игры
    
    Attributes:
        board_size (int): Размер доски
        state (BoardState): Текущее состояние доски
    """
    
    def __init__(self, board_size: int = 19):
        """
        Инициализирует решатель задач.
        
        Args:
            board_size (int): Размер доски (9, 13, или 19)
        
        Raises:
            ValueError: Если размер доски недопустим
        
        Example:
            >>> resolver = TaskResolver(19)
            >>> resolver.state.board_size
            19
        """
        if board_size not in [9, 13, 19]:
            raise ValueError(f"Недопустимый размер доски: {board_size}. Должен быть 9, 13, или 19")
        
        self.board_size = board_size
        self.state = self._create_empty_board(board_size)
    
    def _create_empty_board(self, size: int) -> BoardState:
        """
        Создаёт пустую доску заданного размера.
        
        Args:
            size (int): Размер доски
        
        Returns:
            BoardState: Состояние с пустой доской
        """
        board = [[None for _ in range(size)] for _ in range(size)]
        return BoardState(board=board, board_size=size)
    
    def reset(self):
        """
        Сбрасывает доску в начальное состояние.
        
        Example:
            >>> resolver.make_move(3, 3, "B")
            >>> resolver.reset()
            >>> resolver.state.board[3][3]
            None
        """
        self.state = self._create_empty_board(self.board_size)
    
    def set_initial_position(
        self,
        black_stones: List[Coords],
        white_stones: List[Coords],
        next_color: StoneColor = "B"
    ):
        """
        Устанавливает начальную позицию задачи.
        
        Args:
            black_stones (List[Coords]): Список координат чёрных камней [(x1, y1), ...]
            white_stones (List[Coords]): Список координат белых камней [(x1, y1), ...]
            next_color (StoneColor): Кто ходит следующим
        
        Raises:
            ValueError: Если координаты вне пределов доски
        
        Example:
            >>> resolver.set_initial_position(
            ...     black_stones=[(3, 3), (4, 4)],
            ...     white_stones=[(3, 4)],
            ...     next_color="B"
            ... )
        """
        self.reset()
        
        # Размещаем чёрные камни
        for x, y in black_stones:
            self._validate_coords(x, y)
            self.state.board[y][x] = "B"
        
        # Размещаем белые камни
        for x, y in white_stones:
            self._validate_coords(x, y)
            self.state.board[y][x] = "W"
        
        # Устанавливаем, кто ходит следующим
        self.state.next_color = next_color
    
    def _validate_coords(self, x: int, y: int):
        """
        Проверяет, что координаты находятся в пределах доски.
        
        Args:
            x (int): Координата X (столбец)
            y (int): Координата Y (строка)
        
        Raises:
            ValueError: Если координаты вне пределов
        
        Example:
            >>> resolver._validate_coords(3, 3)  # OK для доски 19x19
            >>> resolver._validate_coords(20, 20)  # ValueError
        """
        if not (0 <= x < self.board_size and 0 <= y < self.board_size):
            raise ValueError(
                f"Координаты ({x}, {y}) вне пределов доски {self.board_size}x{self.board_size}"
            )
    
    def is_valid_move(self, x: int, y: int, color: StoneColor = None) -> bool:
        """
        Проверяет, является ли ход корректным.
        
        Ход считается корректным, если:
        - Координаты в пределах доски
        - Точка пуста
        - Ход не является суицидальным (если включена проверка)
        - Ход не нарушает правило ко
        
        Args:
            x (int): Координата X хода
            y (int): Координата Y хода
            color (StoneColor): Цвет камня (по умолчанию текущий ход)
        
        Returns:
            bool: True если ход корректен
        
        Example:
            >>> resolver.is_valid_move(3, 3)
            True
            >>> resolver.make_move(3, 3, "B")
            >>> resolver.is_valid_move(3, 3)
            False  # Точка занята
        """
        try:
            self._validate_coords(x, y)
        except ValueError:
            return False
        
        # Проверяем, что точка пуста
        if self.state.board[y][x] is not None:
            return False
        
        # Если цвет не указан, используем текущий
        if color is None:
            color = self.state.next_color
        
        # Проверяем на суицидальный ход
        if self._is_suicide_move(x, y, color):
            return False
        
        # Проверяем правило ко
        if self._violates_ko(x, y, color):
            return False
        
        return True
    
    def _is_suicide_move(self, x: int, y: int, color: StoneColor) -> bool:
        """
        Проверяет, является ли ход суицидальным.
        
        Суицидальный ход - это ход, который сразу приводит к захвату
        собственного камня (у камня не остаётся даме после хода).
        
        Args:
            x (int): Координата X
            y (int): Координата Y
            color (StoneColor): Цвет камня
        
        Returns:
            bool: True если ход суицидальный
        """
        # Временно ставим камень
        self.state.board[y][x] = color
        
        # Проверяем, есть ли у камня даме
        liberties = self._count_liberties(x, y)
        
        # Проверяем, захватывает ли этот ход камни противника
        opponent = "W" if color == "B" else "B"
        captures = self._would_capture(x, y, color, opponent)
        
        # Убираем временный камень
        self.state.board[y][x] = None
        
        # Ход суицидальный, если нет даме и нет захватов
        return liberties == 0 and not captures
    
    def _would_capture(
        self,
        x: int,
        y: int,
        color: StoneColor,
        opponent: StoneColor
    ) -> bool:
        """
        Проверяет, захватит ли этот ход камни противника.
        
        Args:
            x (int): Координата X хода
            y (int): Координата Y хода
            color (StoneColor): Цвет делающего ход
            opponent (StoneColor): Цвет противника
        
        Returns:
            bool: True если ход захватывает камни
        """
        # Проверяем соседние точки
        neighbors = self._get_neighbors(x, y)
        
        for nx, ny in neighbors:
            stone = self.state.board[ny][nx]
            if stone == opponent:
                # Проверяем, есть ли у соседней группы даме
                group = self._get_group(nx, ny)
                group_liberties = self._count_group_liberties(group)
                
                # Если после хода у группы не останется даме, она будет захвачена
                if group_liberties == 1 and (x, y) in self._get_group_liberty_points(group):
                    return True
        
        return False
    
    def _violates_ko(self, x: int, y: int, color: StoneColor) -> bool:
        """
        Проверяет, нарушает ли ход правило ко.
        
        Правило ко запрещает повторение позиции, которая уже была на доске.
        
        Args:
            x (int): Координата X
            y (int): Координата Y
            color (StoneColor): Цвет камня
        
        Returns:
            bool: True если ход нарушает правило ко
        """
        # Временно ставим камень
        self.state.board[y][x] = color
        
        # Получаем хэш позиции
        position_hash = self.state.get_position_hash()
        
        # Убираем временный камень
        self.state.board[y][x] = None
        
        # Проверяем, была ли такая позиция
        return position_hash in self.state.previous_positions
    
    def make_move(self, x: int, y: int, color: StoneColor = None) -> bool:
        """
        Выполняет ход на доске.
        
        Args:
            x (int): Координата X хода
            y (int): Координата Y хода
            color (StoneColor): Цвет камня (по умолчанию текущий ход)
        
        Returns:
            bool: True если ход успешен, False если ход некорректен
        
        Example:
            >>> resolver.make_move(3, 3, "B")
            True
            >>> resolver.state.board[3][3]
            "B"
        """
        # Если цвет не указан, используем текущий
        if color is None:
            color = self.state.next_color
        
        # Проверяем корректность хода
        if not self.is_valid_move(x, y, color):
            return False
        
        # Сохраняем текущую позицию для правила ко
        self.state.previous_positions.add(self.state.get_position_hash())
        
        # Ставим камень
        self.state.board[y][x] = color
        self.state.last_move = (x, y)
        
        # Проверяем и удаляем захваченные камни противника
        opponent = "W" if color == "B" else "B"
        captured = self._remove_captured_stones(x, y, color, opponent)
        
        # Обновляем счёт захваченных камней
        if opponent == "W":
            self.state.captured_white += captured
        else:
            self.state.captured_black += captured
        
        # Передаём ход
        self.state.next_color = opponent
        
        return True
    
    def _get_neighbors(self, x: int, y: int) -> List[Coords]:
        """
        Получает соседние точки на доске (сверху, снизу, слева, справа).
        
        Args:
            x (int): Координата X
            y (int): Координата Y
        
        Returns:
            List[Coords]: Список соседних координат
        """
        neighbors = []
        
        # Сверху
        if y > 0:
            neighbors.append((x, y - 1))
        # Снизу
        if y < self.board_size - 1:
            neighbors.append((x, y + 1))
        # Слева
        if x > 0:
            neighbors.append((x - 1, y))
        # Справа
        if x < self.board_size - 1:
            neighbors.append((x + 1, y))
        
        return neighbors
    
    def _get_group(self, x: int, y: int) -> Set[Coords]:
        """
        Получает группу камней того же цвета, к которой принадлежит камень.
        
        Группа - это набор соединённых камней одного цвета.
        
        Args:
            x (int): Координата X камня
            y (int): Координата Y камня
        
        Returns:
            Set[Coords]: Множество координат камней в группе
        """
        color = self.state.board[y][x]
        if color is None:
            return set()
        
        group = set()
        stack = [(x, y)]
        
        while stack:
            cx, cy = stack.pop()
            
            if (cx, cy) in group:
                continue
            
            if self.state.board[cy][cx] != color:
                continue
            
            group.add((cx, cy))
            
            # Добавляем соседей
            for nx, ny in self._get_neighbors(cx, cy):
                if (nx, ny) not in group:
                    stack.append((nx, ny))
        
        return group
    
    def _count_liberties(self, x: int, y: int) -> int:
        """
        Подсчитывает количество даме (свободных точек) у камня.
        
        Args:
            x (int): Координата X камня
            y (int): Координата Y камня
        
        Returns:
            int: Количество даме
        """
        group = self._get_group(x, y)
        return self._count_group_liberties(group)
    
    def _count_group_liberties(self, group: Set[Coords]) -> int:
        """
        Подсчитывает количество даме у группы камней.
        
        Args:
            group (Set[Coords]): Множество координат группы
        
        Returns:
            int: Количество даме
        """
        liberties = set()
        
        for x, y in group:
            for nx, ny in self._get_neighbors(x, y):
                if self.state.board[ny][nx] is None:
                    liberties.add((nx, ny))
        
        return len(liberties)
    
    def _get_group_liberty_points(self, group: Set[Coords]) -> Set[Coords]:
        """
        Получает координаты даме группы.
        
        Args:
            group (Set[Coords]): Множество координат группы
        
        Returns:
            Set[Coords]: Множество координат даме
        """
        liberties = set()
        
        for x, y in group:
            for nx, ny in self._get_neighbors(x, y):
                if self.state.board[ny][nx] is None:
                    liberties.add((nx, ny))
        
        return liberties
    
    def _remove_captured_stones(
        self,
        x: int,
        y: int,
        color: StoneColor,
        opponent: StoneColor
    ) -> int:
        """
        Удаляет захваченные камни противника с доски.
        
        Args:
            x (int): Координата X последнего хода
            y (int): Координата Y последнего хода
            color (StoneColor): Цвет сделавшего ход
            opponent (StoneColor): Цвет противника
        
        Returns:
            int: Количество захваченных камней
        """
        captured_count = 0
        neighbors = self._get_neighbors(x, y)
        
        for nx, ny in neighbors:
            if self.state.board[ny][nx] == opponent:
                group = self._get_group(nx, ny)
                if self._count_group_liberties(group) == 0:
                    # Удаляем захваченную группу
                    for gx, gy in group:
                        self.state.board[gy][gx] = None
                        captured_count += 1
        
        return captured_count
    
    def is_captured(self, x: int, y: int) -> bool:
        """
        Проверяет, захвачен ли камень (у группы не осталось даме).
        
        Args:
            x (int): Координата X камня
            y (int): Координата Y камня
        
        Returns:
            bool: True если камень захвачен
        """
        group = self._get_group(x, y)
        return self._count_group_liberties(group) == 0
    
    def get_liberties(self, x: int, y: int) -> int:
        """
        Получает количество даме у камня.
        
        Args:
            x (int): Координата X камня
            y (int): Координата Y камня
        
        Returns:
            int: Количество даме
        """
        return self._count_liberties(x, y)
    
    def get_board(self) -> List[List[StoneColor]]:
        """
        Получает текущее состояние доски.
        
        Returns:
            List[List[StoneColor]]: Двумерный массив доски
        """
        return deepcopy(self.state.board)
    
    def get_stone(self, x: int, y: int) -> StoneColor:
        """
        Получает камень в указанной точке.
        
        Args:
            x (int): Координата X
            y (int): Координата Y
        
        Returns:
            StoneColor: "B", "W", или None
        """
        self._validate_coords(x, y)
        return self.state.board[y][x]
    
    def get_game_state(self) -> GameState:
        """
        Получает текущее состояние игры.
        
        Returns:
            GameState: ACTIVE, RESIGNED, или SCORED
        """
        return self.state.game_state
    
    def pass_move(self, color: StoneColor = None):
        """
        Выполняет ход пас (пропуск хода).
        
        Args:
            color (StoneColor): Цвет делающего ход
        """
        if color is None:
            color = self.state.next_color
        
        # Сохраняем позицию для правила ко
        self.state.previous_positions.add(self.state.get_position_hash())
        
        # Передаём ход
        self.state.next_color = "W" if color == "B" else "B"
        self.state.last_move = None
    
    def resign(self, color: StoneColor = None):
        """
        Завершает игру сдачей одного из игроков.
        
        Args:
            color (StoneColor): Цвет сдавшегося игрока
        """
        self.state.game_state = GameState.RESIGNED


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

def coords_to_sgf(x: int, y: int) -> str:
    """
    Преобразует координаты в формат SGF.
    
    Args:
        x (int): Координата X
        y (int): Координата Y
    
    Returns:
        str: Координаты в формате SGF (напр. "aa", "dd")
    """
    letters = "abcdefghijklmnopqrstuvwxyz"
    return f"{letters[x]}{letters[y]}"


def sgf_to_coords(sgf: str) -> Coords:
    """
    Преобразует координаты SGF в кортеж (x, y).
    
    Args:
        sgf (str): Координаты в формате SGF
    
    Returns:
        Coords: Кортеж (x, y)
    """
    letters = "abcdefghijklmnopqrstuvwxyz"
    x = letters.index(sgf[0].lower())
    y = letters.index(sgf[1].lower())
    return (x, y)
