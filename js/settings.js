import {app} from "../../scripts/app.js";

const initialState = {
    server: 'https://staging-api.viuport.design',
    timeout: 10,
    userId: '',
    askName: true,
    inputFromFs: false,
    lastName: 'ComfyUi web',
    fsWebWorkflow: null,
    changeMessage: 'Updated workflow...',
}

const uuidv4re = /^[0-9A-F]{8}-[0-9A-F]{4}-[4][0-9A-F]{3}-[89AB][0-9A-F]{3}-[0-9A-F]{12}$/i
const validation = {
    userId: (v) => uuidv4re.test(v) || 'user id must be a valid uuid',
}
export const validState = {}
const validationHandler = {}
export const addValidation = (key, h) => {
    let handlers
    if (key in validationHandler) {
        handlers = validationHandler[key]
    } else {
        handlers = []
        validationHandler[key] = handlers
    }
    handlers.push(h)
}
export const triggerValidation = () => {
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


export const settings = [
    {
        id: "flyingshapes.inputFromFs",
        name: "Input from Flyingshapes",
        type: "boolean",
        defaultValue: true,
    },
    {
        id: "flyingshapes.userId",
        name: "FS-Web UserID",
        type: "string",
        defaultValue: '',
    },
]

const ls = window.localStorage

export const settingsProxy = () => {
    const state = new EventTarget()
    const getProp = p => ['flyingshapes', p].join('.')

    function boundHandler(rootRef) {
        return {
            get(obj, prop) {
                const p = getProp(prop)
                if (typeof obj[prop] === 'function' && obj === rootRef && prop !== 'constructor') {
                    // this returns bound EventTarget functions
                    return obj[prop].bind(obj)
                }
                return app.extensionManager.setting.get(p)
            },
            set(obj, prop, value) {
                const p = getProp(prop)

                try {
                    app.extensionManager.setting.set(p, value)
                    const evData = {
                        detail: {
                            prop, value
                        }
                    }
                    rootRef.dispatchEvent(new CustomEvent('update', evData))
                    rootRef.dispatchEvent(new CustomEvent(`update:${prop}`, evData))
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
    const result = new Proxy(state, boundHandler(state))

    return result
}

export const storageProxy = (name, opts = {}) => {
    const {
        defaults = {},
        lspReset = false,
        storageEventListener = true
    } = opts

    const state = new EventTarget()
    state.lspReset = lspReset

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
                    const evData = {
                        detail: {
                            prop, value
                        }
                    }
                    rootRef.dispatchEvent(new CustomEvent('update', evData))
                    rootRef.dispatchEvent(new CustomEvent(`update:${prop}`, evData))
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

    const result = new Proxy(state, boundHandler(state))

    try {
        const restoredState = JSON.parse(ls.getItem(name)) || {}
        if (restoredState.lspReset !== lspReset) {
            ls.removeItem(name)
            for (const [k, v] of Object.entries({
                ...defaults
            })) {
                result[k] = v
            }
        } else {
            for (const [k, v] of Object.entries({
                ...defaults,
                ...restoredState
            })) {
                result[k] = v
            }
        }
    } catch (e) {
        console.error(e)
        ls.removeItem(name)
    }

    if (storageEventListener && typeof window !== 'undefined' && typeof window.addEventListener !== 'undefined') {
        window.addEventListener('storage', (ev) => {
            // Replace state with whats stored on localStorage... it is newer.
            for (const k of Object.keys(state)) {
                delete result[k]
            }
            const restoredState = JSON.parse(ls.getItem(name)) || {}
            for (const [k, v] of Object.entries({
                ...defaults,
                ...restoredState
            })) {
                result[k] = v
                //result[k] = v
            }
            opts.lspReset = restoredState.lspReset
            //state.dispatchEvent(new Event('update'))
        })
    }

    return result
}

export const state = settingsProxy()
/*
storageProxy(storageKey, {
    defaults: initialState,
})
*/
