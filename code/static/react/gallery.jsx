import {Popup, CSRFSafeSubmit, handleAsyncError, displayPopUp} from './util.jsx'

export default class GalleryList extends React.Component {
    constructor(props) {
        super(props)

        this.state = {
            gallery: [],
            nextPage: 0,
            editable: false
        }

        this.fetchPage = this.fetchPage.bind(this)
        this.handleClick = this.handleClick.bind(this)
    }

    componentDidMount() {
        this.fetchPage(1);
    }

    fetchPage(page) {
        this.setState({page: page})
        fetch(window.location.origin + '/gallery/?page=' + page,
            {
                method: 'POST'
            }
        ).then( (response) => {
            if (!response.ok) {
                throw new Error("Failed to receive response from fetch()")
            }
            return response.json();
        }).then ((json) => {
            var imgElements = []
            for (var i = 0; i < json['gallery'].length; i++) {
                const index = i;
                imgElements.push(<img onClick={(e) => this.handleClick(e, index)} src={window.location.origin + "/gallery/view_preview/" + json['gallery'][i]} index={i} total={json['gallery'].length}/>)
            }
            
            this.setState({srcs: json['gallery'], gallery: imgElements, nextPage: json['next_page'], editable: json['editable'] || false})

        }).catch(handleAsyncError)
    }

    handleClick(e, index) {
        if (e) e.preventDefault()
        displayPopUp(<GalleryPopup callback={this.handleClick} index={index} total={this.state.gallery.length} src={this.state.srcs[index]} editable={this.state.editable}/>)
    }

    render() {
        return (
            <div>
            {this.state.editable? <UploadImageButton/>: ''}
            <div className="galleryList">
                {this.state.gallery}
            </div>
            </div>
        )
    }
}

class GalleryPopup extends React.Component {
    constructor(props) {
        super(props)

        this.state = {
            img: null,
            loading: true,
            title: '',
            editing: false
        }

        this.delete = this.delete.bind(this)
        this.submit = this.submit.bind(this)
        this.handleChange = this.handleChange.bind(this)

        // this isn't good, sorry!
        this.headerRef = React.createRef()
        this.mainRef = React.createRef()
    }

    componentDidMount() {
        fetch(window.location.origin + '/gallery/info/' + this.props.src,
            {
                method: 'GET'
            }
        ).then( (response) => {
            if (!response.ok) {
                throw new Error("Failed to receive response from fetch()")
            }
            return response.json();
        }).then ((json) => {
            this.setState({img:  json, loading: false, message: '', title: json['title']})
        }).catch(handleAsyncError)
    }

    componentDidUpdate(prevProps) {
        if (prevProps.src != this.props.src) {
            this.componentDidMount()
            var editTag = document.getElementById("nameImageEdit")
            if (editTag) editTag.value = this.state.img.name;
        }
    }

    submit(e, token) {
        e.preventDefault()
        const title = document.getElementById("editImageName").value
        fetch(window.location.origin + '/gallery/edit/' + this.props.src,
            {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': "application/json"
                },
                body: JSON.stringify({'title': title, 'token': token})
            }
        ).then( (response) => {
            if (!response.ok) {
                throw new Error("Failed to receive response from fetch()")
            }
            return response.json().then((json) => {
                this.setState({message: json['DESC']})
            }).catch(() => window.location.href = response.url);                
        }).catch(handleAsyncError)
        this.setState({
            loading: true
        })
    }

    delete(e, token) {
        e.preventDefault()
        fetch(window.location.origin + '/gallery/delete/' + this.props.src,
            {
                method: 'POST',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': "application/json"
                },
                body: JSON.stringify({'token': token})
            }
        ).then( (response) => {
            if (!response.ok) {
                throw new Error("Failed to receive response from fetch()")
            }
            return response.json().then((json) => {
                this.setState({message: json['DESC']})
            }).catch(() => {
                window.location.href = response.url;
            });
        }).catch(handleAsyncError)
        this.setState({
            loading: true
        })
    }

    handleChange(e) {
        this.setState({
            title: e.target.value
        })
    }

    render() {
        return (
            <Popup refs={[this.headerRef, this.mainRef]} className="galleryPopup">
            <div ref={this.headerRef /* not very happy about this */ } className="galleryHeader"><h1 style={{display:"flex", justifyContent:"space-between"}}>{this.state.img != null ? 
                (this.props.editable && this.state.editing? <input style={{flexGrow: 2}} id="editImageName" onChange={this.handleChange} value={this.state.title}/>: this.state.img.title) 
                : ''}
                </h1>
                <div style={{display: "flex", flexDirection: "row"}}>
                {this.props.editable ? 
                        <div>
                        <p>{this.state.message}</p>
                        {
                            this.state.editing ? 
                            <CSRFSafeSubmit className="submission" onClick={this.submit} second={{submissionText: "Cancel", onClick:() => this.setState({editing: false}) }} loading={this.state.loading} key={this.props.id} loadingText="Submitting..." submissionText="Submit"/>: 
                            <CSRFSafeSubmit className="submission" onClick={this.delete} second={{submissionText: "Change Title", onClick:() => this.setState({editing: true})}} loading={this.state.loading} key={this.props.id} loadingText="Deleting..." submissionText="Delete"/>
                        }
                        </div>
                        : ''}
                    <div class="submission"> <button onClick={(e) => {window.open(window.location.origin + "/gallery/view_full/" + this.props.src, '_blank') }}>View Full Image</button>
                    <button onClick={(e) => {this.setState({editing: false}); this.props.callback(e, this.props.index - 1)}} disabled={this.props.index == 0} >&lt;</button>
                    <button onClick={(e) => {this.setState({editing: false}); this.props.callback(e, this.props.index + 1)}} disabled={this.props.index == this.props.total - 1} >&gt;</button></div>
                   
                </div>
                </div>
                {this.state.img != null ? <img ref={this.mainRef} className="imageView" src={window.location.origin + "/gallery/view_full/" + this.props.src}/> : ''}
        </Popup>
        )
    }
}

class UploadImageButton extends React.Component {
    constructor(props) {
        super(props)
        this.handleClick = this.handleClick.bind(this)
    }

    handleClick(e) {
        e.preventDefault()
        displayPopUp(<UploadImagePopup/>)
    }

    render() {
        return (
            <button onClick={this.handleClick}>Upload</button>
        )
    }
}

class UploadImagePopup extends React.Component {
    constructor(props) {
        super(props)

        this.state = {
            loading: false,
            message: ''
        }

        this.submit = this.submit.bind(this)
    }

    submit(e) {
        e.preventDefault()
        var form = new FormData(document.getElementById("uploadImageForm"));
        fetch(window.location.origin + '/gallery/upload',
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
                <h1>Upload Image</h1>
                <form id="uploadImageForm" onSubmit={this.submit} encType="multipart/form-data">
                    <p>{this.state.message}</p>
                    <label htmlFor="title">Title:</label>
                    <input type="text" name="title"/>
                    <input type="file" name="file" text="Upload File"/>
                    <br/>
                    <CSRFSafeSubmit loading={this.state.loading} loadingText="Uploading..." submissionText="Upload" popup={true}/>
                </form>
            </Popup>
            
        )
    }
}