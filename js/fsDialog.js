import {ComfyDialog, $el} from "../../scripts/ui.js";
import {mutateState, state} from "./settings.js";

export class FsDialog extends ComfyDialog {
    constructor() {
        super();
        const close_button = $el("button", {
            id: "fs-close-button",
            type: "button",
            textContent: "Close",
            onclick: () => this.close()
        });
        this.userIdEl = $el("div")
        const userIdParent = $el("div.subgrid-cols", [
            "current FS UserId:",
            this.userIdEl
        ])
        this.clickUserHint = $el('div.all-cols', ['Click on an FS user entry below to select the id and connect.']);

        this.optionsGrid = $el("div.fs-grid", {}, [
            userIdParent,
            this.clickUserHint,
            $el('div', {className: 'hd subgrid-cols'}, [
                $el('div', ['Domain']),
                $el('div', ['User'])
            ]),
        ])
        this.optionsGrid.style.setProperty('--fs-grid-cols', '360px 1fr 24px')
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
        const entries = Object.entries(fsInstances)

        while (optionsGrid.children.length > 3) {
            optionsGrid.removeChild(optionsGrid.lastChild)
        }

        this.userIdEl.innerText = userId
        //this.clickUserHint.style.display = userId ? 'none' : 'block'
        this.clickUserHint.innerText = entries.length > 0
            ? 'Click on an FS user entry below to select the id and connect.'
            : 'No FS user entries available. request an FS user id, and vonfirm your request from FS Web'

        for (const [domain, users] of entries) {
            for (const {id, email} of users) {
                const classNames = ['subgrid-cols x']
                if (id === userId) classNames.push('active')
                const className = classNames.join(' ')
                const domEl = $el('div', [domain.replace(/https?:\/\//, '')])
                const usrEl = $el('div', [email])
                const trashEl = $el('div.trash', ['🗑'])
                trashEl.addEventListener('click', e => {
                    e.stopPropagation()
                    mutateState('fsInstances', inst => {
                        const items = inst[domain]
                        items.splice(items.findIndex(u => u.id === id), 1)
                    })
                })
                const el = $el('div', {
                    className,
                    onclick: () => {
                        state.userId = id
                        //this.close()
                    }
                }, [domEl, usrEl, trashEl])
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

    static get instance() {
        return this._instance || (this._instance = new this());
    }
}