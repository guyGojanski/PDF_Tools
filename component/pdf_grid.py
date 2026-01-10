from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal
from component.file_card import FileCard
from component.toolsForPDF import calculate_rotation
from assets.config import *

class PDFGrid(QWidget):
    items_changed = pyqtSignal()

    def __init__(
        self,
        initial_items=None,
        max_items=None,
        on_delete_callback=None,
        click_to_toggle: bool = False,
        drag_enabled: bool = True,
    ):
        super().__init__()
        self.items = initial_items if initial_items else []
        self.max_items = max_items
        self.dragged_item_data = None
        self.on_delete_callback = on_delete_callback
        self.click_to_toggle = click_to_toggle
        self.drag_enabled = drag_enabled
        self.setAcceptDrops(self.drag_enabled)
        self.active_cards = {}
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll = QScrollArea()
        self.scroll.setObjectName("WorkScrollArea")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.grid_container = QWidget()
        self.grid_container.setObjectName("CardGrid")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setContentsMargins(20, 20, 20, 20)
        self.grid_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        )
        self.scroll.setWidget(self.grid_container)
        main_layout.addWidget(self.scroll)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_grid_visuals()

    def resizeEvent(self, event):
        self.refresh_grid_visuals()
        super().resizeEvent(event)

    def get_items(self):
        return self.items

    def add_items_batch(self, new_items_list):
        if self.max_items is not None:
            space_left = self.max_items - len(self.items)
            if space_left <= 0:
                return False
            items_to_add = new_items_list[:space_left]
        else:
            items_to_add = new_items_list
        if not items_to_add:
            return False
        self.items.extend(items_to_add)
        self.refresh_grid_visuals()
        self.items_changed.emit()
        return True

    def add_item(self, item_data):
        if self.max_items is not None and len(self.items) >= self.max_items:
            return False
        self.items.append(item_data)
        self.refresh_grid_visuals()
        self.items_changed.emit()
        return True

    def remove_item_by_data(self, item_data):
        if item_data in self.items:
            self.items.remove(item_data)
            item_id = id(item_data)
            if item_id in self.active_cards:
                card = self.active_cards.pop(item_id)
                card.deleteLater()
            self.refresh_grid_visuals()
            self.items_changed.emit()

    def handle_delete_action(self, item_data):
        if self.on_delete_callback:
            self.on_delete_callback(item_data)
        else:
            self.remove_item_by_data(item_data)

    def update_rotation(self, item_data):
        if item_data in self.items:
            try:
                item_data["rotation"] = calculate_rotation(item_data["rotation"])
                card = self.active_cards.get(id(item_data))
                if card:
                    card.update_content(item_data)
            except Exception as e:
                print(f"Error updating rotation: {e}")

    def refresh_grid_visuals(self, full_reload=False):
        available_width = self.scroll.viewport().width()
        if available_width < 400:
            available_width = GRID_MIN_FALLBACK_WIDTH
        available_width -= GRID_CONTAINER_PADDING
        card_total_width = FILE_CARD_WIDTH + GRID_CARD_SPACING
        columns = max(GRID_MIN_COLUMNS, available_width // card_total_width)
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        current_active_ids = set()
        for i, item_data in enumerate(self.items):
            item_id = id(item_data)
            current_active_ids.add(item_id)
            card = self.active_cards.get(item_id)
            if not card:
                card = FileCard(
                    item_data, index=i + 1, click_to_toggle=self.click_to_toggle
                )
                card.delete_requested.connect(
                    lambda d=item_data: self.handle_delete_action(d)
                )
                card.rotate_requested.connect(
                    lambda d=item_data: self.update_rotation(d)
                )
                self.active_cards[item_id] = card
            else:
                card.set_number(i + 1)
                if self.dragged_item_data and item_data == self.dragged_item_data:
                    card.set_placeholder(True)
                else:
                    card.set_placeholder(False)
            row = i // columns
            col = i % columns
            self.grid_layout.addWidget(card, row, col)
        ids_to_remove = []
        for item_id, card in self.active_cards.items():
            if item_id not in current_active_ids:
                card.deleteLater()
                ids_to_remove.append(item_id)
        for item_id in ids_to_remove:
            del self.active_cards[item_id]

    def get_card_by_data(self, item_data):
        return self.active_cards.get(id(item_data))

    def dragEnterEvent(self, event):
        if not self.drag_enabled:
            event.ignore()
            return
        if event.mimeData().hasText():
            event.accept()
            path = event.mimeData().text()
            for item in self.items:
                if item["path"] == path:
                    self.dragged_item_data = item
                    break
            self.refresh_grid_visuals()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if not self.drag_enabled:
            event.ignore()
            return
        event.accept()
        if not self.dragged_item_data:
            return
        target_widget = self.childAt(event.position().toPoint())
        target_card = None
        while target_widget:
            if isinstance(target_widget, FileCard):
                target_card = target_widget
                break
            target_widget = target_widget.parent()
        if target_card:
            try:
                current_index = self.items.index(self.dragged_item_data)
                target_item_data = target_card.item_data
                target_index = self.items.index(target_item_data)
                if current_index != target_index:
                    item = self.items.pop(current_index)
                    self.items.insert(target_index, item)
                    self.refresh_grid_visuals()
                    self.items_changed.emit()
            except ValueError:
                pass

    def dropEvent(self, event):
        if not self.drag_enabled:
            event.ignore()
            return
        self.dragged_item_data = None
        self.refresh_grid_visuals()
        event.accept()
