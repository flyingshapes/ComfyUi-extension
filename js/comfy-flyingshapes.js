import {app} from "../../scripts/app.js";
import {api} from "../../scripts/api.js";
import {ComfyDialog, $el} from "../../scripts/ui.js";

const style = `
#fs-manager-dialog {
	width: 480px;
	/*height: 520px;*/
	box-sizing: content-box;
	z-index: 10000;
}
.fs-title {
	/*background-color: black;*/
	text-align: center;
	height: 40px;
	width: calc(100% - 10px);
	font-weight: bold;
	justify-content: center;
	align-content: center;
	vertical-align: middle;
}
.comfy-modal-content.gap {
    gap: 20px;
}
.fs-grid {
    display: grid;
    grid-template-columns: 100px 1fr;
}
.fs-validation-error {
    /*position: absolute;*/
    /*top: -120%;*/
    /*top: 0;*/
    color: var(--error-text);
    grid-column: span 2;
    /*display: none;*/
}
`

export var fs_dialog_instance = null;
const storageKey = 'flyingshapes'
const uuidv4re = /^[0-9A-F]{8}-[0-9A-F]{4}-[4][0-9A-F]{3}-[89AB][0-9A-F]{3}-[0-9A-F]{12}$/i
const validation = {
    userId: (v) => uuidv4re.test(v) || 'user id must be a valid uuid',
}
const validState = {}
const validationHandler = {}
const addValidation = (key, h) => {
    let handlers
    if (key in validationHandler) {
        handlers = validationHandler[key]
    } else {
        handlers = []
        validationHandler[key] = handlers
    }
    handlers.push(h)
}

var fsButtons = {
    settings: undefined,
    sendWorkflow: undefined,
};


const getExtraData = () => {
    const {lspReset, userId, ...s} = JSON.parse(ls.getItem(storageKey)) || {}
    return {...s, userId}
}

app.registerExtension({
    name: "flyingshapes.menu",
    init() {
        $el("style", {
            textContent: style,
            parent: document.head,
        });

        const keybindListener = function (event) {
            const {ctrlKey, shiftKey, key} = event
            const modifierPressed = ctrlKey && shiftKey

            const modifierKeyIdMap = {
                S: "#fs-send-workflow-button",
            };

            const modifierKeybindId = modifierKeyIdMap[event.key];
            if (modifierPressed && modifierKeybindId) {
                event.preventDefault();

                const elem = document.querySelector(modifierKeybindId);
                elem.click();
            }
        }

        window.addEventListener("keydown", keybindListener, true);
    },
    async setup() {
        //await new Promise(resolve => setTimeout(resolve, 50))

        const menu = document.querySelector(".comfy-menu");
        //const queueButton = document.querySelector("#queue-button");
        //async queuePrompt(number, batchCount = 1) {
        //const originalQueue = queueButton.onclick
        const origQueuePrompt = app.queuePrompt
        app.queuePrompt = async (...args) => {
            console.log("Sending FS Prompt...")
            await sendExtraData()
            await origQueuePrompt.call(app, ...args);
        }

        let order = 50
        const items = []
        const makeEl = (...args) => {
            const elem = $el(...args)
            elem.style.order = order++
            menu.append(elem)
            return elem
        }
        makeEl("hr", {
            style: {
                margin: "20px 0 0 0",
                width: "100%",
            },
        })
        makeEl("h3", {
            style: {
                order: order++,
                margin: "10px 0",
            },
        }, ["Flyingshapes"])

        fsButtons.settings = makeEl("button", {
            id: "fs-settings-button",
            onclick: () => {
                if (!fs_dialog_instance) fs_dialog_instance = new FsDialog()
                fs_dialog_instance.show()
                triggerValidation()
            }
        }, [
            "Settings"
        ])

        fsButtons.sendWorkflow = makeEl("button", {
            id: "fs-send-workflow-button",
            onclick: pushWorkflowToFs
        }, [
            "send workflow"
        ])
    },
    async provideExtraData() {
        return {fs_data: getExtraData()}
    }
})

function createInput(id0, label, inputType = "text", wrapDiv = false) {
    const id = `fs_${id0}`;
    const attr = inputType === "checkbox" ? "checked" : "value"
    const update = () => {
        state[id0] = input_el[attr]
        console.log(`updating ${id0}: ${state[id0]}`)
    }
    const input_el = $el("input", {
        type: inputType,
        id,
        min: 0,
        onkeyup: update,
        onchange: update
    }, [])
    input_el[attr] = state[id0]

    const input_el_text = $el("label", {for: id}, [label])
    input_el_text.style.color = "var(--fg-color)";
    input_el_text.style.cursor = "pointer";

    const valid_message = $el("div", {
        className: "fs-validation-error"
    }, [])
    //valid_message.style.backgroundColor = "var(--error-text)";
    //valid_message.style.color = "var(--error-text)";
    //valid_message.style.visibility = "hidden";
    addValidation(id0, (msg) => {
        if (msg === true) {
            valid_message.style.display = "none";
        } else {
            valid_message.style.display = "block";
            valid_message.innerHTML = msg
        }
    })

    const result = [valid_message, input_el_text, input_el]

    if (wrapDiv) {
        return [$el("div", {}, result)]
    } else return result
}

const ls = window.localStorage
if (!ls) {
    alert('Your Browser does not support localstorage. The FS extension will not work.')
}

const storageProxy = (name, opts = {}) => {
    const {
        defaults = {},
        lspReset = false,
        storageEventListener = true
    } = opts

    const state = new EventTarget()
    try {
        const restoredState = JSON.parse(ls.getItem(name)) || {}
        if (restoredState.lspReset !== lspReset) {
            ls.removeItem(name)
            for (const [k, v] of Object.entries({
                ...defaults
            })) {
                state[k] = v
            }
        } else {
            for (const [k, v] of Object.entries({
                ...defaults,
                ...restoredState
            })) {
                state[k] = v
            }
        }
    } catch (e) {
        console.error(e)
        ls.removeItem(name)
    }

    state.lspReset = lspReset

    if (storageEventListener && typeof window !== 'undefined' && typeof window.addEventListener !== 'undefined') {
        window.addEventListener('storage', (ev) => {
            // Replace state with whats stored on localStorage... it is newer.
            for (const k of Object.keys(state)) {
                delete state[k]
            }
            const restoredState = JSON.parse(ls.getItem(name)) || {}
            for (const [k, v] of Object.entries({
                ...defaults,
                ...restoredState
            })) {
                state[k] = v
            }
            opts.lspReset = restoredState.lspReset
            state.dispatchEvent(new Event('update'))
        })
    }

    function boundHandler(rootRef) {
        return {
            get(obj, prop) {
                if (typeof obj[prop] === 'object' && obj[prop] !== null) {
                    return new Proxy(obj[prop], boundHandler(rootRef))
                } else if (typeof obj[prop] === 'function' && obj === rootRef && prop !== 'constructor') {
                    // this returns bound EventTarget functions
                    return obj[prop].bind(obj)
                } else {
                    return obj[prop]
                }
            },
            set(obj, prop, value) {
                obj[prop] = value
                try {
                    ls.setItem(name, JSON.stringify(rootRef))
                    rootRef.dispatchEvent(new Event('update'))
                    return true
                } catch (e) {
                    console.error(e)
                    return false
                }
            },
            // has(obj, key) {
            //     return key in obj;
            // },
        }
    }

    return new Proxy(state, boundHandler(state))
}

const initialState = {
    server: 'https://staging-api.viuport.design',
    timeout: 10,
    userId: '',
    askName: true,
    lastName: 'ComfyUi web'
}
const state = storageProxy(storageKey, {
    defaults: initialState,
})

const triggerValidation = () => {
    for (const [k, f] of Object.entries(validation)) {
        const data = state[k]
        const validResult = f(data)
        validState[k] = validResult
        if (k in validationHandler) {
            const handlers = validationHandler[k]
            for (const handler of handlers) {
                handler(validResult, data)
            }
        }
    }
}

state.addEventListener('update', triggerValidation)

class FsDialog extends ComfyDialog {
    constructor() {
        super();
        const close_button = $el("button", {
            id: "fs-close-button",
            type: "button",
            textContent: "Close",
            onclick: () => this.close()
        });
        const content =
            $el("div.comfy-modal-content.gap",
                [
                    $el("tr.fs-title", {}, [
                        $el("font", {size: 6, color: "white"}, [`Flyingshapes`])]
                    ),
                    $el("div.fs-grid",
                        [
                            ...this.createControls()
                            //$el("div.cm-menu-column", [...this.createControls()]),
                            // $el("div.cm-menu-column", [...this.createControlsMid()]),
                            // $el("div.cm-menu-column", [...this.createControlsRight()])
                        ]),

                    close_button,
                ]
            );

        content.style.width = '100%';
        content.style.height = '100%';

        this.element = $el("div.comfy-modal", {id: 'fs-manager-dialog', parent: document.body}, [content]);
    }

    createControls() {
        const server_input = createInput("server", "Server")
        const user_id = createInput("userId", "User Id")
        const timeout = createInput("timeout", "Timeout (s)", "number")
        const askName = createInput("askName", "Ask for name?", "checkbox")


        return [
            //...server_input,
            ...user_id,
            ...timeout,
            ...askName,
        ]
    }
}

/**
 *
 * @param {string} endPoint
 * @param {object} data
 * @returns {Promise<void>}
 */
async function postRequest(endPoint, data, catchErr = false) {
    const clientId = api.initialClientId ?? api.clientId
    try {
        const response = await api.fetchApi(`/flyingshapes/${endPoint}`, {
            method: "POST",
            body: JSON.stringify({...data, clientId}),
        })
        if (!response.ok) {
            const data = await response.json()
            console.error(data)
            app.ui.dialog.show(data.error ?? "Unknown Error.");
            throw data
        } else try {
            return await response.json()
        } catch (e) {
            return { error: await response.text() }
        }
    } catch (e) {
        console.error(e)
        if (!catchErr) throw e
    }
}

async function sendExtraData() {
    const extraData = getExtraData()
    await postRequest("extra-data", {extraData})
}

async function pushWorkflowToFs() {
    const {output: workflow} = await app.graphToPrompt();
    const {userId, askName, lastName} = state
    const data = {workflow, userId}
    if (askName) {
        const name  = prompt("Send workflow to FS, enter a name:", lastName)
        if (name == null) return
        state.lastName = name
        if (name) data.name = name
    }
    await postRequest("push-workflow", data)
}