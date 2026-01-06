from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QScrollArea
from PyQt6.QtCore import Qt, pyqtSignal
from component.file_card import FileCard
from component.toolsForPDF import calculate_rotation


class PDFGrid(QWidget):
    items_changed = pyqtSignal()

    def __init__(self, initial_items=None, max_items=20):
        super().__init__()
        self.items = initial_items if initial_items else []
        self.max_items = max_items
        self.dragged_item_data = None
        self.setAcceptDrops(True)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setObjectName("MergeScrollArea")
        scroll.setWidgetResizable(True)
        self.grid_container = QWidget()
        self.grid_container.setObjectName("GridContainer")
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        scroll.setWidget(self.grid_container)
        main_layout.addWidget(scroll)
        self.refresh_grid_visuals(full_reload=True)

    def get_items(self):
        return self.items

    def add_item(self, item_data):
        if len(self.items) >= self.max_items:
            return False
        self.items.append(item_data)
        self.refresh_grid_visuals(full_reload=True)
        self.items_changed.emit()
        return True

    def remove_item_by_data(self, item_data):
        if item_data in self.items:
            self.items.remove(item_data)
            self.refresh_grid_visuals(full_reload=True)
            self.items_changed.emit()

    def update_rotation(self, item_data):
        if item_data in self.items:
            item_data["rotation"] = calculate_rotation(item_data["rotation"])

    def refresh_grid_visuals(self, full_reload=False):
        if full_reload:
            while self.grid_layout.count():
                item = self.grid_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            columns = 4
            for i, item_data in enumerate(self.items):
                card = FileCard(item_data, index=i + 1)
                card.delete_requested.connect(
                    lambda d=item_data: self.remove_item_by_data(d)
                )
                card.rotate_requested.connect(
                    lambda d=item_data: self.update_rotation(d)
                )
                row = i // columns
                col = i % columns
                self.grid_layout.addWidget(card, row, col)
        else:
            widgets = []
            for i in range(self.grid_layout.count()):
                widgets.append(self.grid_layout.itemAt(i).widget())
            for i, widget in enumerate(widgets):
                if i < len(self.items):
                    item_data = self.items[i]
                    if isinstance(widget, FileCard):
                        if widget.file_path != item_data[
                            "path"
                        ] or widget.page_num != item_data.get("page", 0):
                            widget.update_content(item_data)
                        widget.set_number(i + 1)
                        if (
                            self.dragged_item_data
                            and item_data == self.dragged_item_data
                        ):
                            widget.set_placeholder(True)
                        else:
                            widget.set_placeholder(False)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.accept()
            path = event.mimeData().text()
            for item in self.items:
                if item["path"] == path:
                    self.dragged_item_data = item
                    break
            self.refresh_grid_visuals(full_reload=False)
        else:
            event.ignore()

    def dragMoveEvent(self, event):
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
                    self.refresh_grid_visuals(full_reload=False)
                    self.items_changed.emit()
            except ValueError:
                pass

    def dropEvent(self, event):
        self.dragged_item_data = None
        self.refresh_grid_visuals(full_reload=False)
        event.accept()
