import {app} from "../../scripts/app.js";
import {api} from "../../scripts/api.js";
import {ComfyDialog, $el} from "../../scripts/ui.js";
import {
    loadWorkflowFromFsWeb, pushWorkflowToFs, getFsConnection, requestEditWorkflow, sendExtraData,
    requestFsWebUserId
} from "./requests.js";
import {icons} from "./fsimg.js";
import {settings, state, addValidation, triggerValidation} from "./settings.js";
import {loadCss, addCss} from "./common.js"

//const basePath = 'extensions/ComfyUi-FS-extension/assets'

const style = `
:root {
    --fs-icon: ${icons.fsIcon().dataUrlCss};
    --fs-logo: ${icons.fsLogo().dataUrlCss};
}
`

addCss(style)
//background-image: url("${basePath}/FS-Icon-256.png");
loadCss('./fs.css')

let fs_dialog_instance = null;
export function getDialogInstance() {
    if (!fs_dialog_instance) fs_dialog_instance = new FsDialog()
    //console.log(fs_dialog_instance)
    return fs_dialog_instance
}
const emptyImage = 'data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACADs='

let fsButtons = {
    //settings: undefined,
    requestFsId: undefined,
    sendWorkflow: undefined,
    requestWebWorkflow: undefined,
    saveFsWeb: undefined
};

let connectedInterval = undefined
/**
 * @type {undefined | HTMLElement}
 */
let connectedDisplayParent = undefined

/**
 *
 * @param {object} els
 * @returns {{vals: {}, keys: {}, flat: *[]}}
 */
function makeEls(els){
    const keys = {}
    const vals = {}
    const flat = []
    for (const [k, v] of Object.entries(els)) {
        const elK = $el("div", {className: "key",}, [k])
        const elV = $el("div", {className: "val",}, [v])
        keys[`${k}Kel`] = elK
        vals[`${k}Vel`] = elV
        flat.push(elK, elV)
    }

    return {keys, vals, flat}
}


const menu = document.createElement('div')
menu.classList.add('flyingshapes-menu')

app.extensionManager.registerSidebarTab({
    id: "flyingshapes",
    icon: "fs-icon",
    title: "flyingshapes",
    tooltip: "flyingshapes",
    type: "custom",
    render: (el) => {
        //el.innerHTML = "<div>Custom search tab</div>";
        el.appendChild(menu)
    },
});

// userId: '',
//     askName: true,
//     inputFromFs: false,

app.registerExtension({
    name: "flyingshapes.menu",
    init() {
        const keybindListener = function (event) {
            const {ctrlKey, shiftKey, key} = event
            const modifierPressed = ctrlKey && shiftKey

            const modifierKeyIdMap = {
                F: "#fs-send-workflow-button",
                S: "#fs-save-workflow-web",
                O: "#fs-request-web-workflow",
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
        //const menu = document.querySelector(".comfy-menu");
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
        const fsVrLabel = $el("span", {}, ["FS VR"])
        const fsWebLabel = $el("span", {}, ["FS Web"])
        const connectedDisplayEl = $el("span", {
            className: "connection-bubble vr",
        })

        const connectedDisplayElWeb = $el("span", {
            className: "connection-bubble web",
        })

        const settingsIcon = $el("span", {
                    id: "fs-settings-button",
                    className: "comfy-btn fs-settings-button",
                    onclick: e => {
                        e.stopPropagation()
                        getDialogInstance().show()
                        triggerValidation()
                    }
                }, [
                    "⚙️"
        ])

        const makeEl = (...args) => {
            const elem = $el(...args)
            //elem.style.order = order++
            menu.append(elem)
            return elem
        }

        const makeGrid = ({cols, gap, class: cls}, ...args) => {
            let className = 'fs-grid all-cols'
            if (cls) className += ` ${cls}`
            const el = makeEl("div", {
                className,
            }, args)

            if (cols) el.style.setProperty('--fs-grid-cols', cols)
            if (gap) el.style.setProperty('--fs-gap', gap)

            return el
        }

        fsButtons.requestFsId = makeEl("div", {
            id: "fs-request-fs-id",
            style: {
                display: 'flex',
                gap: '10px',
                alignItems: 'center',
            },
        }, [
            $el("button", {
                id: "fs-request-fs-id-button",
                //className: "comfy-btn fs-settings-button",
                style: {
                    flexGrow: 1,
                },
                onclick: () => {
                    requestFsWebUserId()
                }
            }, [
                "Request FS ID",
            ]),
            settingsIcon
        ])

        connectedDisplayParent = makeEl("div", {
            style: {
                //order: order++,
                margin: "10px 0",
            },
            className: "connected-display all-cols"
        }, [fsVrLabel, connectedDisplayEl, fsWebLabel, connectedDisplayElWeb])

        fsButtons.requestWebWorkflow = makeEl("button", {
            id: "fs-request-web-workflow",
            onclick: requestEditWorkflow,
        }, [
            "Open workflow"
        ])

        fsButtons.sendWorkflow = makeEl("button", {
            id: "fs-send-workflow-button",
            onclick: () => pushWorkflowToFs()
        }, [
            "send to VR"
        ])

        fsButtons.saveFsWeb = $el("button", {
            id: "fs-save-workflow-web",
            className: 'all-cols',
            onclick: () => pushWorkflowToFs(true)
        }, [
            "save (FS web)"
        ])

        makeGrid({cols: '125px 1fr'},
            //...createInput("userId", "User Id"),
            ...createInput("inputFromFs", "Input from FS?", "checkbox")
        )

        //makeEl('div', {}, createInput("userId", "User Id"))
        //makeEl('div', {}, createInput("inputFromFs", "Input from FS?", "checkbox"))
        //const user_id = createInput("userId", "User Id")
        //const inputFromFs = createInput("inputFromFs", "Input from FS?", "checkbox")
        //menu.append(...user_id, ...inputFromFs)


        clearInterval(connectedInterval)
        triggerValidation()
        connectedInterval = setInterval(() => getFsConnection(connectedDisplayParent), 2500)
        addValidation('userId', () => getFsConnection(connectedDisplayParent))

        const {flat, vals: {nameVel, descVel, updVel}} = makeEls({
            name: "workflow-name",
            desc: "workflow-description",
            upd: "updated-at"
        })

        const closeMenuButton = $el("button", {
            className: "close comfy-close-menu-btn",
            onclick: () => state.fsWebWorkflow = undefined
        }, ["×"])

        const openedWfInfo = makeEl("div", {
            id: "fs-web-opened-wf"
        }, [closeMenuButton, ...flat, fsButtons.saveFsWeb])

        const updateFsWebWorkflow = (value) => {
            if (value) {
                const {description, id, name, updatedAt} = value
                console.log(id)
                nameVel.innerHTML = name
                descVel.innerHTML = description
                updVel.innerHTML = updatedAt
                openedWfInfo.classList.add('show')
            } else {
                openedWfInfo.classList.remove('show')
            }
        }

        updateFsWebWorkflow(state.fsWebWorkflow)

        state.addEventListener('update:fsWebWorkflow', (e) => {
            const value = e.detail?.value
            updateFsWebWorkflow(value)
        })

        const updateOptions = e => {
            getDialogInstance().updateOptions()
        }

        state.addEventListener('update:fsInstances', updateOptions)
        state.addEventListener('update:userId', updateOptions)
        //getFsConnection
    },
    settings,
    nodeCreated(node, app) {
        if (node.comfyClass === 'FLYINGSHAPES_Input_Screen_Shot') {
            // const w = node.widgets.find(obj => obj.name === 'stored_value');
            // //node.widgets.length = 0
            // Object.defineProperty(w, 'value', {
            //     set(v) {
            //         if(v != '[IMAGE DATA]')
            //             w._value = v;
            //         app.graph.setDirtyCanvas(true);
            //     },
            //     get() {
            //         return w._value
            //         const stackTrace = new Error().stack;
            //         if(!stackTrace.includes('draw') && !stackTrace.includes('graphToPrompt') && stackTrace.includes('app.js')) {
            //             return "[IMAGE DATA]";
            //         }
            //         else {
            //             return w._value;
            //         }
            //     }
            // });
            // console.log(node.widgets)
            // const set_img_act = (v) => {
            //     node._img = v;
            //     var canvas = document.createElement('canvas');
            //     canvas.width = v[0].width;
            //     canvas.height = v[0].height;
            //
            //     var context = canvas.getContext('2d');
            //     try {
            //         context.drawImage(v[0], 0, 0, v[0].width, v[0].height);
            //     } catch (e) {
            //         console.error("drawimage failed")
            //         return;
            //     }
            //
            //     var base64Image = canvas.toDataURL('image/png')
            //     w.value = base64Image.split(',')[1]
            // };
            //
            // Object.defineProperty(node, 'imgs', {
            //     set(v) {
            //         if (!v[0].complete) {
            //             let orig_onload = v[0].onload;
            //             v[0].onload = function(v2) {
            //                 if(orig_onload)
            //                     orig_onload();
            //                 set_img_act(v);
            //             };
            //         }
            //         else {
            //             set_img_act(v);
            //         }
            //     },
            //     get() {
            //         if (this._img == undefined) {
            //             const img = new Image()
            //             this._img = img
            //             img.onerror = (e) => {
            //                 this._img0.src = emptyImage;
            //             }
            //             img.onload = (e) => {
            //                 app.graph.setDirtyCanvas(true);
            //                 this._img0.src = img.src
            //             }
            //
            //         }
            //         if (this._img0 === undefined) {
            //             this._img0 = new Image()
            //         }
            //         if (this._imgs === undefined) {
            //             this._imgs = [this._img0];
            //         }
            //
            //         if(w.value && w.value !== '[IMAGE DATA]') {
            //             const imgSrc = `data:image/png;base64,${w.value}`
            //             if (this._img.src !== imgSrc) {
            //                 this._img.src = imgSrc
            //             }
            //         }
            //
            //         return this._imgs;
            //     }
            // });
        }
    }
})

function createInput(id0, label, inputType = "text", wrapDiv = false) {
    const id = `fs_${id0}`;
    const attr = inputType === "checkbox" ? "checked" : "value"
    const update = () => {
        state[id0] = input_el[attr]
        console.log(`updating ${id0}: ${state[id0]}`);
    }
    const input_el = $el("input", {
        type: inputType,
        id,
        min: 0,
        onkeyup: update,
        onchange: update
    }, [])
    const readFromSettings = () => {
        input_el[attr] = state[id0]
    }
    state.addEventListener(`update:${id0}`, readFromSettings)
    readFromSettings()

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
        this.userIdEl = $el("div.subgrid-cols", {})
        this.optionsGrid = $el("div.fs-grid", {}, [
            this.userIdEl,
            $el('div', {className: 'hd subgrid-cols'}, [
                $el('div', ['Domain']),
                $el('div', ['User'])
            ]),
        ])
        this.optionsGrid.style.setProperty('--fs-grid-cols', '360px 1fr')
        const content =
            $el("div.comfy-modal-content.gap",
                [
                    $el("tr.fs-title", {}, [
                        $el("font", {size: 6, color: "white"}, [`Flyingshapes Connection`])]
                    ),
                    this.optionsGrid,

                    close_button,
                ]
            );

        content.style.width = '100%';
        content.style.height = '100%';

        this.updateOptions()

        this.element = $el("div.comfy-modal", {id: 'fs-manager-dialog', parent: document.body}, [content]);
    }

    updateOptions() {
        const {optionsGrid} = this
        const {fsInstances, userId} = state

        while (optionsGrid.children.length > 2) {
            optionsGrid.removeChild(optionsGrid.lastChild)
        }

        this.userIdEl.innerText = userId

        for (const [domain, users] of Object.entries(fsInstances)) {
            for (const {id, email} of users) {
                const classNames = ['subgrid-cols x']
                if (id === userId) classNames.push('active')
                const className = classNames.join(' ')
                const domEl = $el('div', {}, [domain.replace(/https?:\/\//, '')])
                const usrEl = $el('div', {}, [email])
                const el = $el('div', {
                    className,
                    onclick: () => {
                        state.userId = id
                        //this.close()
                    }
                }, [domEl, usrEl])
                optionsGrid.appendChild(el)
            }
        }

        // const options = {
        //     server: state.server,
        //     userId: state.userId,
        //     timeout: state.timeout,
        //     askName: state.askName,
        //     inputFromFs: state.inputFromFs,
        // }
        // this.options = options
    }

    createControls() {
        this.updateOptions()
        // const server_input = createInput("server", "Server")
        // const user_id = createInput("userId", "User Id")
        // const timeout = createInput("timeout", "Timeout (s)", "number")
        // const askName = createInput("askName", "Ask for name?", "checkbox")
        // const inputFromFs = createInput("inputFromFs", "Input from FS?", "checkbox")


        return [
            //...server_input,
            // ...user_id,
            // ...timeout,
            // ...askName,
            // ...inputFromFs,
        ]
    }
}

const loadWorkflowFromFsWebEvent = 'fs-api-load-workflow'
api.addEventListener(loadWorkflowFromFsWebEvent, loadWorkflowFromFsWeb)