// @ts-nocheck
// The module 'vscode' contains the VS Code extensibility API
// Import the module and reference it with the alias vscode in your code below
const vscode = require('vscode');
const sendCode = require('./sendCode');
const child_process = require('child_process');
const path = require('path');
const os = require('os');
const fs = require('fs');


function saveToFile(code) {
    if (code) {
        var temp = os.tmpdir();
        var filePath = temp +"/StataRun"+Date.now();
        filePath +='.do';
         fs.writeFile(filePath, code + "\n", (err) => {
             if (err) throw err;
             console.log('The file has been saved!');
           });
         const doFileCommand = 'do '+filePath;
         return sendCode.send(doFileCommand);
         //vscode.window.showInformationMessage(filePath);
     }
     else {
        let mgs = 'Document is empty'
        vscode.window.showWarningMessage(mgs);
     }
}
// this method is called when your extension is activated
// your extension is activated the very first time the command is executed

function CheckEditor(editor) {
    if (!editor) {
        let mgs = 'No Editor is opened. Open a compatible file and try again'
        vscode.window.showWarningMessage(mgs);
    }
    else {
        return editor;
    }
}

function ShowError() {
    let mgs = 'The editor look empty, please adding some stata code or command'
    vscode.window.showErrorMessage(mgs);
}

function activate(context) {

    // Use the console to output diagnostic information (console.log) and errors (console.error)
    // This line of code will only be executed once when your extension is activated
    console.log('Congratulations, your extension "stataRun" is now active!');

    // run all command
    let runAllShow = vscode.commands.registerTextEditorCommand('stataRun.runAllShow', function (editor) {
        // --- Define Script Path INSIDE command --- Added/Moved ---
        const scriptDir = path.dirname(context.extensionPath); // context is available here
        const fullPreprocessScriptPath = path.join(scriptDir, 'stataRun', 'preprocess_stata_for_show.py');
        // --- End Define Script Path ---

        vscode.commands.executeCommand('workbench.action.files.save');
        var code = editor.document.getText();

        // --- Preprocessing Step --- Added Block ---
        let processedCode = code; // Default to original code if preprocessing fails
        try {
            // Check if script exists before running
            if (!fs.existsSync(fullPreprocessScriptPath)) {
                throw new Error(`Preprocessing script not found at ${fullPreprocessScriptPath}`);
            }

            console.log(`stataRunShow: Preprocessing with ${fullPreprocessScriptPath}`);
            const pythonExecutable = '~/.ssl585/bin/python3'; // Or determine dynamically if needed
            // Execute the python script synchronously, passing code via stdin
            processedCode = child_process.execSync(`${pythonExecutable} "${fullPreprocessScriptPath}"`, {
                input: code,
                encoding: 'utf-8',
                maxBuffer: 100 * 1024 * 1024 // Allow up to 10MB buffer (adjust if needed) -> 10 -> 100 *1024 *1024
            });
            console.log(processedCode);
            console.log('stataRunShow: Preprocessing successful.');
        } catch (error) {
            console.error('stataRunShow: Error during preprocessing:', error);
            vscode.window.showErrorMessage(`stataRunShow Preprocessing Error: ${error.message}. Running original code instead.`);
            processedCode = code; // Explicitly ensure original code is used on error
            // Optional: uncomment below to prevent running original code on error
            // return; 
        }
        // --- End Preprocessing Step ---

        saveToFile(processedCode); // Use processedCode here
    });
    
    context.subscriptions.push(runAllShow); // Ensure runAllShow is pushed

    let runSelection = vscode.commands.registerCommand('stataRun.runSelection', function () {
        // Run Selection text
        let editor = CheckEditor(vscode.window.activeTextEditor)
        if (editor){
            let selection = editor.selection;
            let code = editor.document.getText(selection);
            if (code){
                saveToFile(code)
            }
            else {
                ShowError()
            }
        }
        context.subscriptions.push(runSelection);

    });

    let runDown = vscode.commands.registerCommand('stataRun.runDown', function () {
        // Run Selection from current line to bottom
        let editor = CheckEditor(vscode.window.activeTextEditor)
        if (editor){
            const position = editor.selection.active.line
            const lines = editor.document.lineCount -1
            const first = new vscode.Position(position,0)
            const lastpos= editor.document.lineAt(lines)
            const last = new vscode.Position(lines,lastpos.range.end.character)

            if (first != last) {
                const range = new vscode.Range(first,last);
                var code = editor.document.getText(range);
            }
            if (code){
                saveToFile(code)
            }
            else {
                ShowError()
            }
        }
        context.subscriptions.push(runDown);

    });
    let runCurrent = vscode.commands.registerCommand('stataRun.runCurrent', function () {
        // Run Selection from current line to bottom
        let editor = CheckEditor(vscode.window.activeTextEditor)
        if (editor){
            const position = editor.selection.active
            const first = new vscode.Position(position.line,0)
            const lastpos= editor.document.lineAt(position.line)
            const last = new vscode.Position(position.line, lastpos.range.end.character)
            if (first != last) {
                const range = new vscode.Range(first, last);
                var code = editor.document.getText(range);
            }
            if (code){
                saveToFile(code)
            }
            else {
                ShowError()
            }
        }
        context.subscriptions.push(runCurrent);
    });

    let runFront= vscode.commands.registerCommand('stataRun.runFront', function () {
        // Run Selection from current line to bottom
        let editor = CheckEditor(vscode.window.activeTextEditor)
        if (editor){
            const position = editor.selection.active.line
            const first = new vscode.Position(0,0)
            const lastpos= editor.document.lineAt(position)
            const last = new vscode.Position(position,lastpos.range.end.character)
            if (first != last) {
                const range = new vscode.Range(first,last);
                var code = editor.document.getText(range);
            }
            if (code){
                saveToFile(code)
            }
            else {
                ShowError()
            }
        }
        context.subscriptions.push(runFront);

    });
}

// this method is called when your extension is deactivated
function deactivate() {
    // Clean up any resources or subscriptions
    context.subscriptions.forEach(subscription => subscription.dispose());
}

module.exports = {
    activate,
    deactivate
};