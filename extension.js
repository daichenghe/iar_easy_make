"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
// The module 'vscode' contains the VS Code extensibility API
const vscode = require("vscode");
// const TreeViewProvider_1 = require("./TreeViewProvider");
const TreeViewProvider = require("./TreeViewProvider");
const WebView_1 = require("./WebView");
const resolve = require('path');

let extension_path = __dirname;

let emake_script = extension_path + './iar_make.py'
var terminalA;
function activate(context) {
    // TreeViewProvider_1.TreeViewProvider.initTreeViewItem();
    TreeViewProvider.TreeViewProvider_init.initTreeViewItem();

    context.subscriptions.push(vscode.commands.registerCommand('itemClick', (label) => {

    // for(var j = 0; vscode.window.terminals[j]!=null; j++) {
    //     vscode.window.showErrorMessage('name: ' + vscode.window.terminals[j].name);
    // }
    // var my_extension_path = vscode.extensions.getExtension(this).extensionPath;
    // vscode.window.showInformationMessage('name: ' + extension_path);
    var is_open = false;
    is_open = vscode.window.terminals.map((item) => {
        if (item.name === "aceinna_shell") {
            return true;
        }

    });
    if(is_open == false)
    {
        terminalA = vscode.window.createTerminal({ name: "aceinna_shell" });
        terminalA.show(true);
    }

    if(label == 'build')
    {
        terminalA.show(true);
        var cmd = 'python ' + emake_script + ' build iar_make.mk';
        terminalA.sendText(cmd);
    }
    else if(label == 'rebuild')
    {
        terminalA.show(true);
        var cmd = 'python ' + emake_script + ' rebuild iar_make.mk';
        terminalA.sendText(cmd);
    }
    else if(label == 'clean')
    {
        terminalA.show(true);
        var cmd = 'python ' + emake_script + ' clean iar_make.mk';
        terminalA.sendText(cmd);
    }

    }));
}
exports.activate = activate;
function deactivate() { }
exports.deactivate = deactivate;
//# sourceMappingURL=extension.js.map