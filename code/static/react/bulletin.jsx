import {Popup, CSRFSafeSubmit, handleAsyncError, displayPopUp} from './util.jsx'

export default class BulletinList extends React.Component {
    constructor(props) {
        super(props);

        this.state = {
            message: '',
            editable: false,
            editing: false,
            loading: false,
            selected: [],
            bulletins: {},
            page : 1
        }

        this.delete = this.delete.bind(this)
        this.changeCheckbox = this.changeCheckbox.bind(this)
    }

    componentDidMount() {
        this.fetchPage(1);
    }

    fetchPage(page) {
        this.setState({page: page})
        fetch(window.location.origin + '/bulletin/' + page,
            {
                method: 'POST'
            }
        ).then( (response) => {
            if (!response.ok) {
                throw new Error("Failed to receive response from fetch()")
            }
            return response.json();
        }).then ((json) => {
            this.setState({bulletins: json['posts'], nextPage: json['next_page'], editable: json['editable'] || false, editing: false, selected: []})
        }).catch(handleAsyncError)
    }

    changeCheckbox(event) {
        var target = event.target
        var selected = this.state.selected
        if (target.checked) {
            selected.push(target.value)
        } else {
            selected = selected.filter((x) => x != target.value)
        }
        
        this.setState({
            selected: selected
        })
    }

    delete(e, token) {
        e.preventDefault()
        fetch(window.location.origin + "/bulletin/delete", {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({'links': this.state.selected, 'token': token})
        }).then((response) => {
            if (!response.ok) {
                throw new Error("Failed to receive response from fetch()")
            }
            this.setState({loading: false})
            return response.json().then((json) => {
                this.setState({message: json['DESC'], selected:[]})
            }).catch(() => {
                window.location.href = response.url;
            })
        }).catch(handleAsyncError)
        this.setState({loading: true})
    }

    render() {
        var bulletinElements = []
        for (var i in this.state.bulletins) {
            var b = this.state.bulletins[i]
            bulletinElements.push(<li>{this.state.editing? <div><input type="checkbox" onChange={this.changeCheckbox} value={b['link']}/> {b['title']}</div>: <a target="_blank" href={'/bulletin/' + b['link']}>{b['title']}</a>}</li>)
        }
        return (
            <div>
                <div className="bulletinHeader">
                    <h2>Bulletins</h2>
                    {this.state.editable? <div><AddBulletinButton/>
                    <button type="button" onClick={() => this.setState({editing: !this.state.editing})}>{!this.state.editing? 'Edit' : 'Cancel'}</button>
                    </div>: ''}
                </div>
                <p>{this.state.message}</p>
                {bulletinElements}
                <div className="pages" hidden={this.state.page == 1 && !this.state.nextPage}>
                    <button onClick={() => this.fetchPage(this.state.page - 1)} disabled={this.state.page == 1}>&lt;</button>
                    <p>{this.state.page}</p>
                    <button onClick={() => this.fetchPage(this.state.page + 1)} disabled={!this.state.nextPage}>&gt;</button>
                </div>
                {this.state.editing? <CSRFSafeSubmit loading={this.state.loading} loadingText="Deleting..." submissionText="Delete" disabled={this.state.selected.length < 1} onClick={this.delete}/> : ''}
            </div>
        )
    }
}

class AddBulletin extends React.Component {
    constructor(props) {
        super(props)

        this.submit = this.submit.bind(this);

        this.state = {
            message: '',
            loading: false
        }
    }

    submit(e) {
        e.preventDefault();
        var form = new FormData(document.getElementById("uploadBulletinForm"));
        fetch(window.location.origin + '/bulletin/upload',
            {
                method: 'POST',
                body: form,
                credentials: 'same-origin'
            }
        ).then( (response) => {
            if (!response.ok) {
                throw new Error("Failed to receive response from fetch()")
            }
            return response.json().then((json) => {
                this.setState({message:json['DESC'], loading:false})
            }).catch(() => {
                window.location.href = response.url;
            });
        }).catch((e) => {
            this.setState({loading: false})
            handleAsyncError(e)
        });
        this.setState({loading: true})
    }

    render() {
        return (
            <Popup>
                <h1>Upload Bulletin</h1>
                <form id="uploadBulletinForm" onSubmit={this.submit} encType="multipart/form-data">
                    <p>{this.state.message}</p>
                    <label htmlFor="title">Title:</label>
                    <input type="text" name="title"/>
                    <input type="file" name="file" text="Upload File"/>
                    <br/>
                    <CSRFSafeSubmit loading={this.state.loading} loadingText="Uploading..." submissionText="Confirm" popup={true}/>
                </form>
            </Popup>
        )
    }
}

class AddBulletinButton extends React.Component {
    render() {
        return (
            <button onClick={() => displayPopUp(<AddBulletin/>)}>+</button>
        )
    }
}