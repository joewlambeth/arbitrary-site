export class Popup extends React.Component {
    constructor(props) {
        super(props);
        this.myRef = React.createRef();
        this.defocus = this.defocus.bind(this);
    }

    defocus(e) {
        if (this.myRef.current && !this.myRef.current.contains(e.target)) {
            tearDownPopup();
        } else if ("refs" in this.props) {
            
            var toTearDown = !this.props.refs.some((ref) => ref.current.contains(e.target));
            for (var i = 0; i < this.props.refs.length; i++) {
                console.log(this.props.refs[i].current.contains(e.target));
            }
            console.log("-----" + toTearDown)
            if (toTearDown) tearDownPopup();
        }
    }

    componentDidMount() {
        document.addEventListener('mousedown', this.defocus);
    }

    componentWillUnmount() {
        document.removeEventListener('mousedown', this.defocus);
    }

    render() {
        console.log(this.props.refs)
        return (
            <div ref={"refs" in this.props? "" : this.myRef} className={this.props['className'] || "container"} style={{width: this.props.width, height: this.props.height}} onClick={this.defocus}>
            {this.props.children}
            </div>
        );
    }
}

export class DialogPopup extends React.Component {

}

export class CSRFSafeSubmit extends React.Component {
    constructor(props){
        // TODO: take array of secondary actions...
        super(props)

        this.defaultLoadingText = "Loading..."
        this.defaultSubmissionText = "Submit"

        this.state = {
            token: "",
        }
    }
    
    componentDidMount() {
        fetch('/token', {
            method: 'GET'
        }).then( (response) => {
            return response.json()
        }).then( (json) => {
            this.setState({
                token: json['token']
            })
        })
    }

    render() {
        return (
            <div className={this.props.className || "submission"}>
                <input hidden={true} name="token" value={this.state.token} readOnly={true}/>
                <button disabled={this.state.token == null || this.props.loading || this.props.disabled} type={this.props.onClick ? "button":"submit"} onClick={this.props.onClick ? (e) => this.props.onClick(e, this.state.token) : ''} >{this.props.loading ? this.props.loadingText || this.defaultLoadingText : this.props.submissionText || this.defaultSubmissionText}</button>
                {this.props.popup ? <button type="button" style={ {float:'right'} } onClick={tearDownPopup}>Cancel</button> : ''}
                {!this.props.popup && this.props.second ? <button style={{float:'right'}} onClick={(e) => this.props.second.onClick(e, this.state.token)}>{this.props.second.submissionText}</button>: ''}
            </div>
        )
    }
}

export function handleAsyncError(e) {
    alert("Error communicating with the server!")
    console.error(e.message)
}

export function displayPopUp(comp) {
    ReactDOM.render(
        comp,
        document.getElementById("popUp")
    );
    const popUp = document.getElementById("popUp")
    popUp.style.height = "100%";
}

export function getParameterByName(name) {
    return window.location.href.replace(new RegExp(/.*[\?\&]/.source + name + /=([^\?&]+).*/.source), /$1/.source)
}

function tearDownPopup() {
    ReactDOM.render(
        '',
        document.getElementById("popUp")
    )
    document.getElementById("popUp").style.height = "0";
}
