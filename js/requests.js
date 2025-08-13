import {api} from "../../scripts/api.js";
import {state, validState} from "./settings.js";

/**
 *
 * @param {string} endPoint
 * @param {object} data
 * @param catchErr if true, exceptions are caught, otherwise rethrown
 * @param showError if true and the request returns with an error, the error is shown via ui dialog
 * @returns {Promise<any>}
 */
async function postRequest(endPoint, data, catchErr = false, showError = true) {
    const clientId = api.initialClientId ?? api.clientId
    try {
        const response = await api.fetchApi(`/flyingshapes/${endPoint}`, {
            method: "POST",
            body: JSON.stringify({...data, clientId}),
        })
        if (!response.ok) {
            const data = await response.json()
            if (showError)  app.ui.dialog.show(data.error ?? "Unknown Error.");
            // noinspection ExceptionCaughtLocallyJS
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

const getExtraData = () => {
    const keys = Object.getOwnPropertyNames(state)
    const data = Object.fromEntries(keys.map(k => [k, state[k]]))
    const {lspReset, userId, ...s} = data || {}
    return {...s, userId}
}

export async function sendExtraData() {
    const extraData = getExtraData()
    await postRequest("extra-data", {extraData})
}

export async function pushWorkflowToFs(web = false) {
    const {output, workflow: workflow_ui} = await app.graphToPrompt();
    const {userId, askName, lastName, fsWebWorkflow, changeMessage} = state
    /*workflow*/
    const data = {workflow: output, workflow_ui, userId}
    console.error(fsWebWorkflow)

    if (web) {
        if (!fsWebWorkflow) {
            app.ui.dialog.show(`No workflow from FS Web Opened`);
            return
        }
        const {id, name} = fsWebWorkflow
        const change_message  = prompt("What has changed", changeMessage)
        if (change_message == null) return
        //app.ui.dialog.show(`Workflow not saved.`);

        state.changeMessage = change_message
        Object.assign(data, {
            id,
            name,
            change_message,
            fs_id_prefix: 'web'
        })
    } else if (askName) {
        const name  = prompt("Send workflow to FS, enter a name:", lastName)
        if (name == null) return
        state.lastName = name
        if (name) data.name = name
    }
    await postRequest("push-workflow", data)
}

export async function requestEditWorkflow() {
    const {userId} = state
    /*workflow*/
    const data = {userId}

    try {
        const result = await postRequest("request-workflow-edit", data, false, false)
        console.log('Received result:', result)
        const {workflow: {
            graphUi,
            id,
            name,
            updatedAt,
            description
        }} = result

        state.fsWebWorkflow = {id, name, description, updatedAt}
        app.ui.dialog.show(`Opened workflow '${name}' from FS Web. Description: "${description}"`);
        await app.loadGraphData(graphUi);
    } catch (e) {
        if (e.cancelled) {
            app.ui.dialog.show("The request to open a workflow was declined from FS Web.");
        } else if (e.error) {
            app.ui.dialog.show(`An error occurred: ${e.error}`);
            console.error(e)
        } else {
            app.ui.dialog.show("An unknown error occurred, when trying to open a workflow from FS Web.");
            console.error(e)
        }
    }
}

export async function getFsConnection(elem) {
    const {userId} = state
    if (!elem) return
    const uidValid = validState['userId'] === true
    if (uidValid) {
        elem.classList.add('valid')
    } else {
        elem.classList.remove('valid')
    }
    try {
        let result = await postRequest("fs-connection", {userId}, undefined, false)
        //console.log(result)
        if (result.connected) {
            elem.classList.add('connected')
        } else {
            elem.classList.remove('connected')
        }
        if (result.connectedWeb) {
            elem.classList.add('connected-web')
        } else {
            elem.classList.remove('connected-web')
        }
    } catch (e) {
        elem.classList.remove('connected', 'connected-web')
        console.log(e)
    }
}

/**
 * receives a workflow from fs-web
 * @param {string} id the workflow id, as stored in fs-web db
 * @param {string} name the workflow name
 * @param {object} apiWorkflow the workflow in api-format
 * @param {object} originalWorkflow if stored, the workflow with node positions
 * @param {object} detail all data from the event
 * @returns {Promise<void>}
 */
export async function loadWorkflowFromFsWeb({ detail: { id, name, apiWorkflow, originalWorkflow }, detail }) {
    console.log(id, name, apiWorkflow, originalWorkflow)

    const idIsString = typeof id === "string" && uuidv4re.test(id)
    if (!idIsString) {
        const error = `received ${loadWorkflowFromFsWebEvent}, but no valid id`
        console.error(error, detail)
        alert(error)
        return
    }

    if (!name) console.warn('received unnamed workflow')
    name ??= `unnamed (${id})`

    state.fsWebWorkflow = {id, name}

    if (originalWorkflow) {
        await app.loadGraphData(originalWorkflow);
    } else if (app.isApiJson(apiWorkflow)) {
        app.loadApiJson(apiWorkflow);
    } else {
        const error = `received ${loadWorkflowFromFsWebEvent}, but missing workflow data`
        console.error(error, detail)
        alert(error)
    }
}