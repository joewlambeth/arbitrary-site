import {Popup, CSRFSafeSubmit, handleAsyncError, displayPopUp} from './util.jsx'

export default class LoginButton extends React.Component {
    render() {
        return (
            <button onClick={() => displayPopUp(<Login/>)}> Site Login </button>
        );
    }
}

class Login extends React.Component {
    constructor(props) {
        super(props);

        this.submit = this.submit.bind(this);

        this.state = {
            message: null,
            loading: false,
            key: 1,
            password: ''
        }
    }

    submit(e) {
        e.preventDefault();
        var form = new FormData(document.getElementById("loginForm"));
        fetch(window.location.origin + '/login',
            {
                method: 'POST',
                body: form,
                credentials: 'same-origin',
                redirect: 'follow'
            }
        ).then( (response) => {
            if (!response.ok) {
                throw new Error("Failed to receive response from fetch()")
            }
            return response.json().then((json) => {
                // this approach implies that a non-JSON response is a redirect
                // it's a nasty approach, but it works here
                this.setState({
                    message: json['DESC'],
                    password: '',
                    key: this.state.key < 1024 ? this.state.key + 1 : 1,
                    loading: false
                })
            }).catch(() => {
                // redirect
                window.location.href = response.url;
            });
        }).catch((e) => {
            this.setState({loading: false})
            handleAsyncError(e)
        });

        this.setState({
            message: null,
            loading: true
        })
    }

    render() {
        return (
            <Popup>
            <h1>Login</h1>
            <form id="loginForm" onSubmit={this.submit} className="login">
                <p>{this.state.message}</p>
                <label htmlFor="username">Username:</label>
                <input type="text" name="username"/>
                <label htmlFor="password">Password:</label>
                <input type="password" id="loginPassword" value={this.state.password} onChange={(e) => this.setState({password: e.target.value})} name="password"/>
                <CSRFSafeSubmit loadingText="Logging in" loading={this.state.loading} key={this.state.key} submissionText='Login' popup={true}/>
            </form>
            </Popup>
        );
    }
}