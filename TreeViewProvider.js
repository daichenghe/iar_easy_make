"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const vscode_1 = require("vscode");
const path_1 = require("path");
const ITEM_ICON_MAP = new Map([
    ['build',  'make.svg'],
    ['rebuild', 'build.svg'],
    ['clean',  'clean.svg']
]);


class TreeItemNode extends vscode_1.TreeItem {
    constructor(label, collapsibleState) {
        super(label, collapsibleState);
        this.label = label;
        this.collapsibleState = collapsibleState;
        this.command = {
            title: this.label,
            command: 'itemClick',
            tooltip: this.label,
            arguments: [
                this.label,
            ]
        };
        this.iconPath = TreeItemNode.getIconUriForLabel(this.label);
    }
    static getIconUriForLabel(label) {
        return vscode_1.Uri.file(path_1.join(__filename, '..', 'media', ITEM_ICON_MAP.get(label) + ''));
    }
}
exports.TreeItemNode = TreeItemNode;
class TreeViewProvider_1 {
    getTreeItem(element) {
        return element;
    }
    getChildren(element) {
        return ['build', 'rebuild', 'clean'].map(item => new TreeItemNode(item, vscode_1.TreeItemCollapsibleState.None));
    }
}

class TreeViewProvider_init
{
    static initTreeViewItem() {
        const treeViewProvider1 = new TreeViewProvider_1();
        vscode_1.window.registerTreeDataProvider('tree_iar', treeViewProvider1);
    }
}

exports.TreeViewProvider_1 = TreeViewProvider_1;
exports.TreeViewProvider_init = TreeViewProvider_init;
