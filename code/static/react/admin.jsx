import {CSRFSafeSubmit, handleAsyncError} from './util.jsx'

export default class AdminPanel extends React.Component {
    constructor (props) {
        super(props)

        this.queryList = this.queryList.bind(this)
        this.switchContext = this.switchContext.bind(this)

        this.state = {
            mode: '',
            id: -1,
            items: [],
            registerOptions: {}
        }

        this.modeComponents = {
            'user': () => <AdminUserPanel registerOptions={this.state.registerOptions} id={this.state.id}/>,
            'group': () => <AdminGroupPanel registerOptions={this.state.registerOptions} id={this.state.id}/>,
            'activity': () => <AdminActivityPanel/>,
            '': () => <div className="adminPanelHome">
                <button onClick={() => this.switchContext('user')}type="button">Manage Users</button>
                <button onClick={() => this.switchContext('group')}type="button">Manage Groups</button>
                <button onClick={() => this.switchContext('activity')}type="button">View Activity Log</button>
                </div>
        }

        this.editable = ['user', 'group']
    }

    switchContext(mode) {
        this.setState({
            mode: mode,
            items: {}
        })
        if (this.editable.includes(mode)) {
            this.queryList(mode)
        }
        
    }

    queryList(mode) {
        fetch(window.location.origin + "/admin/" + mode, {
            method: "GET"
        }).then((response) => {
            if (!response.ok) {
                throw new Error("Failed to receive response from fetch()")
            }
            return response.json()
        }).then((json) => {
            this.setState({
                items: json['NAMES']
            })
        }).catch(handleAsyncError)
    }

    componentDidMount() {
        fetch(window.location.origin + "/admin/", {
            method: "POST"
        }).then((response) => {
            return response.json()
        }).then((json) => {
            this.setState({
                registerOptions: json
            })
        }).catch(handleAsyncError)
    }

    render() {
        var nameElements = []
        for (const i in this.state.items) {
            const item = this.state.items[i]
            nameElements.push(<li className={this.state.id == i ? 'selected': ''} onClick={() => this.setState({id: i})} key={i}>{item}</li>)
        }
        return ( 
        <div>
            <div className="adminList">
                <div className="buttonRow">
                    <button id="back" disabled={this.state.mode == ''} onClick={() => this.setState({mode: '', id: -1})} type="button">Back</button>
                    <button id="add" disabled={!this.editable.includes(this.state.mode)} onClick={() => this.setState({id: 0})}type="button">+</button>
                </div>
                { this.state.mode != '' ? <div> <ul>{nameElements} </ul> </div> : ''}
            </div>
            <div className="adminPane">
                {this.modeComponents[this.state.mode]()}
            </div>
        </div> )
    }
}

class AdminUserPanel extends React.Component {
    constructor(props) {
        super(props)

        this.state = {
            loading: false,
            user: {},
            message: '',
            boxes: {'permissions':{}, 'groups':{}}
        }

        this.changeCheckbox = this.changeCheckbox.bind(this)
        this.updateRegisterOptions = this.updateRegisterOptions.bind(this);
        this.submit = this.submit.bind(this)
        this.delete = this.delete.bind(this)

    }

    updateRegisterOptions(user) {
        var boxes = {}
        for (var section in this.props.registerOptions) {
            if (!(section in boxes)) boxes[section] = {}
            for (var item in this.props.registerOptions[section]) {
                boxes[section][item] = {'checked': user.hasOwnProperty(section) && user[section].includes(item),
                                        'enabled': true}
            }
            for (var item in this.props.registerOptions[section]) {
                if (boxes[section][item]['checked'] && typeof this.props.registerOptions[section][item] == 'object') {
                    for (var i in this.props.registerOptions[section][item]) {
                        const child = this.props.registerOptions[section][item][i]
                        boxes[section][child] = {'checked': false, 'enabled': false}
                    }
                }
            }
        }
        this.setState({
            boxes: boxes
        })
    }

    changeCheckbox(event) {
        var target = event.target
        var boxes = this.state.boxes
        boxes[target.name][target.value]['checked'] = target.checked
        if (typeof this.props.registerOptions[target.name][target.value] === 'object') {
            for (var i in this.props.registerOptions[target.name][target.value]) {
                const child = this.props.registerOptions[target.name][target.value][i]
                boxes[target.name][child]['enabled'] = !target.checked
                boxes[target.name][child]['checked'] = false;
            }
        }
        
        this.setState({
            boxes: boxes
        })
    }

    componentDidUpdate(nextProps) {
        if (nextProps.id !== this.props.id) {
            const form = document.getElementById("editUserForm")
            if (form !== null) {
                form.reset()
                this.setState({
                    user: {}
                })
            }
            if (this.props.id > 0) {
                fetch(window.location.origin + "/admin/user/" + this.props.id, {
                    method: "GET"
                }).then((response) => {
                    if (!response.ok) {
                        throw new Error("Failed to receive response from fetch()")
                    }
                    return response.json()
                }).then((json) => {
                    json['groups'] = json['groups'].map(x => x.toString())
                    this.setState({
                        user: json
                    })
                    this.updateRegisterOptions(json)
                }).catch(handleAsyncError)
            } else if (this.props.id == 0) {
                this.updateRegisterOptions({})
            }
        }
        
        if (nextProps.registerOptions !== this.props.registerOptions) {
            this.updateRegisterOptions(this.state.user)
        }


    }

    submit(e) {
        var form = new FormData(document.getElementById("editUserForm"));
        e.preventDefault()
        var suffix = '/admin/user'
        if (this.props.id >= 1) {
            suffix += '/' + this.props.id + '/edit'
        } else {
            suffix += '/register'
        }
        fetch(window.location.origin + suffix, {
            method: 'POST',
            body: form,
            credentials: 'same-origin'
        }).then((response) => {
            if (!response.ok) {
                throw new Error("Failed to receive response from fetch()")
            }
            return response.json().then((json) => {
                this.setState({
                    message: json['DESC'],
                    loading: false
                })
            }).catch(() => {
                window.location.href = response.url;
            })
        }).catch(handleAsyncError)
        this.setState({loading: true})
    }

    delete(e, token) {
        e.preventDefault()
        fetch(window.location.origin + '/admin/user/' + this.props.id + '/delete', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': "application/json"
            },
            body: JSON.stringify({'token': token})
        }).then((response) => {
            if (!response.ok) {
                throw new Error("Failed to receive response from fetch()")
            }
            return response.json().then((json) => {
                this.setState({
                    message: json["DESC"]
                })
            }).catch(() => {
                window.location.href = response.url;
            })
        }).catch(handleAsyncError)
    }

    render () {
        if (this.props.id == -1) {
            return (<p>Select a user to edit them, or click '+' to add a new one.</p>)
        } else {
            var values = {}
            for (const section in this.state.boxes) {
                values[section] = []
                for (const [item, value] of Object.entries(this.state.boxes[section])) {
                    const registerOption = this.props.registerOptions[section][item]
                    values[section].push(<div className="boxAndLabel"><label htmlFor={item}>{typeof registerOption == 'string'? registerOption: item}</label>
                    <input onChange={this.changeCheckbox} disabled={!value['enabled']} checked={value['checked']} name={section} value={item} type="checkbox" /></div>)
                }
            }

            return (
            <form key={this.props.id} id="editUserForm" onSubmit={this.submit}>
                <h2>{this.state.message}</h2>
                <div className="formEntry">
                    <label htmlFor="username">Username:</label>
                    <input name="username" type="text" defaultValue={'username' in this.state.user ? this.state.user.username : ''} disabled={'username' in this.state.user} ></input>
                </div>
                <div className="formEntry">
                    <label htmlFor="password">Password:</label>
                    <input name="password" type="password"></input>
                </div>
                <div className="formEntry">
                    <label htmlFor="password2">Re-enter Password:</label>
                    <input name="password2" type="password"></input>
                </div>
                <div className="formEntry"  style={{ justifyContent: "space-around", alignItems: "flex-start"}}>
                    <div className="checkboxList">
                        <p>Permissions:</p>
                        {values['permissions']}
                    </div>
                    <div className="checkboxList">
                        <p>Groups:</p>
                        {values['groups']}
                    </div>
                </div>
                
                <CSRFSafeSubmit second={{submissionText: "Delete", onClick:this.delete}}loading={this.state.loading} key={this.props.id} loadingText="Uploading..." submissionText="Confirm"/>
            </form>)
        }
    }
}

class AdminGroupPanel extends React.Component {
    constructor(props) {
        super(props)

        this.state = {
            loading: false,
            group: {},
            message: ''
        }

        this.submit = this.submit.bind(this)
        this.delete = this.delete.bind(this)
    }

    componentDidUpdate(nextProps) {
        if (nextProps.id !== this.props.id) {
            const form = document.getElementById("editGroupForm")
            if (form !== null) {
                form.reset()
                this.setState({
                    group: {}
                })
            }
            if (this.props.id > 0) {
                fetch(window.location.origin + "/admin/group/" + this.props.id, {
                    method: "GET"
                }).then((response) => {
                    if (!response.ok) {
                        throw new Error("Failed to receive response from fetch()")
                    }
                    return response.json()
                }).then((json) => {
                    this.setState({
                        group: json
                    })
                    console.log(json)
                }).catch(handleAsyncError)
            }
        }
    }

    changeButtons(e) {

    }

    submit(e) {
        var form = new FormData(document.getElementById("editGroupForm"));
        e.preventDefault()
        var suffix = '/admin/group'
        if (this.props.id >= 1) {
            suffix += '/' + this.props.id + '/edit'
        } else {
            suffix += '/add'
        }
        fetch(window.location.origin + suffix, {
            method: 'POST',
            body: form,
            credentials: 'same-origin'
        }).then((response) => {
            if (!response.ok) {
                throw new Error("Failed to receive response from fetch()")
            }
            return response.json().then((json) => {
                this.setState({
                    message: json['DESC'],
                    loading: false
                })
            }).catch(() => {
                window.location.href = response.url;
            })
        }).catch(handleAsyncError)
        this.setState({loading: true})
    }

    delete(e, token) {
        e.preventDefault()
        fetch(window.location.origin + '/admin/group/' + this.props.id + '/delete', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
                'Content-Type': "application/json"
            },
            body: JSON.stringify({'token': token})
        }).then((response) => {
            if (!response.ok) {
                throw new Error("Failed to receive response from fetch()")
            }
            return response.json().then((json) => {
                this.setState({
                    message: json["DESC"]
                })
            }).catch(() => {
                window.location.href = response.url;
            })
        }).catch(handleAsyncError)
    }

    render () {
        if (this.props.id == -1) {
            return (<p>Select a group to edit them, or click '+' to add a new one.</p>)
        } else {
            return (
                <div>
                <form key={this.props.id} id="editGroupForm" onSubmit={this.submit}>
                    <h2>{this.state.message}</h2>
                    <div className="formEntry">
                        <label htmlFor="title">Title:</label>
                        <input name="title" type="text" defaultValue={'title' in this.state.group ? this.state.group.title : ''}></input>
                    </div>
                    <div className="formEntry" style={{margin: "10px", justifyContent: "space-around"}}>
                        <div><input id="groups" type="radio" name="grouptype" value="groups" defaultChecked={!('grouptype' in this.state.group) || this.state.group.grouptype == 'groups'}/><label htmlFor="groups">Ministries & Groups</label></div>
                        <div><input id="connect" type="radio" name="grouptype" value="connect" defaultChecked={'grouptype' in this.state.group && this.state.group.grouptype == 'connect'}/><label htmlFor="connect">Serve & Connect</label></div>
                    </div>
                    <label htmlFor="description">Description:</label>
                    <div className="formEntry"  style={{ justifyContent: "space-around", alignItems: "flex-start"}}>
                        <textarea style={{width: "50%"}} name="description" defaultValue={'description' in this.state.group ? this.state.group.description : ''}></textarea>
                        <textarea style={{width: "30%"}} readOnly={true} value={this.state.group.hasOwnProperty('users') ? this.state.group.users.join('\n') : ''}></textarea>
                    </div>
                    <CSRFSafeSubmit second={{submissionText: "Delete", onClick:this.delete}} loading={this.state.loading} key={this.props.id} loadingText="Submitting..." submissionText="Confirm"/>
                    </form>
                </div>
            )
        }
    }
}

class AdminActivityPanel extends React.Component {
    constructor(props) {
        super(props)

        this.state = {
            activities: []
        }
    }

    componentDidMount() {
        fetch(window.location.origin + "/admin/activity", {
            method: "POST"
        }).then((response) => {
            if (!response.ok) {
                throw new Error()
            }
            return response.json()
        }).then((json) => {
            this.setState({
                activities: json
            })
        }).catch(handleAsyncError)
    }

    render() {
        return (
            <div className="activityList"><ul>{this.state.activities}</ul></div>
        )
    }
}