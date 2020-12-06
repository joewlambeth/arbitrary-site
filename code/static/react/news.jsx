import {handleAsyncError, getParameterByName} from './util.jsx'

export default class NewsDropdowns extends React.Component {
    constructor(props) {
        super(props)

        this.state = {
            tags: null,
            groups: null,
            groupsChosen: false
        }

        this.radioButtonChange = this.radioButtonChange.bind(this)
    }

    componentDidMount() {
        const result = window.location.pathname.match(/\/news\/(\d)\/edit/)
        fetch(window.location.origin + '/news/' + (result ? result[1] : '') , {
            method: 'POST',
            credentials: 'same-origin'
        }).then((response) => {
            if (!response.ok) {
                throw new Error()
            }
            return response.json()
        }).then((json) => {
            this.setState({
                ...json, 
                groupsChosen: json['group'] && json['group'] != -1
            })

            // recheck state for query params
            const categoryType = getParameterByName('categoryType')
            this.setState({
                groupsChosen: categoryType && categoryType == 'group',
                group: getParameterByName('group'),
                tag: getParameterByName('tag')
            })
        }).catch(handleAsyncError)
    }

    radioButtonChange(e) {
        this.setState({
            groupsChosen: e.target.value == 'group'
        })
    }

    render() {
        console.log(this.state)
        return (<div class="newsDropdowns">
            <div style={{display: "flex", flexDirection: "column"}}>
                <div><input name="categoryType" type="radio" disabled={this.state.tags == null} checked={!this.state.groupsChosen} onChange={this.radioButtonChange} value="tags"/><label htmlFor="tags">Tags</label></div>
                <div><input name="categoryType" type="radio" disabled={!this.state.groups || this.state.groups.length < 1} checked={this.state.groupsChosen} onChange={this.radioButtonChange} value="group"/><label htmlFor="group">Groups</label></div>
            </div>
            <div style={{flexGrow: 1}}>
                <TagDropdown noNewTags={this.props.noNewTags} hidden={this.state.groupsChosen} default={this.state.tag || -1} disabled={this.state.groupsChosen || this.state.tags == null} tags={this.state.tags}/>
                <GroupDropdown hidden={!this.state.groupsChosen} default={this.state.group || -1} disabled={!this.state.groupsChosen || this.state.groups == null} groups={this.state.groups} />
            </div>
        </div>)
    }
}

class GroupDropdown extends React.Component {
    constructor(props) {
        super(props)

        this.state = {
            dropdownValue: -1
        }
    
        this.changeDropdownValue = this.changeDropdownValue.bind(this)
    }

    componentDidUpdate(prevProps) {
        if (prevProps.default != this.props.default) {
            this.setState({
                dropdownValue: this.props.default
            })
        }
    }

    changeDropdownValue(e) {
        this.setState({
            dropdownValue: e.target.value
        })
    }

    render() {
        var groupOptions = []
        var connectOptions = []
        if (this.props.groups) {
            for (const [k, v] of Object.entries(this.props.groups['groups'])) {
                groupOptions.push(<option value={k}>{v}</option>)
            }
            
            for (const [k, v] of Object.entries(this.props.groups['connect'])) {
                connectOptions.push(<option value={k}>{v}</option>)
            }
        }
        
        return (
        <div className="tagDropdown" style={this.props.hidden? {display: "none"}: {}}>
            <label htmlFor="group">Group: </label>
            <select value={this.props.disabled? -1: this.state.dropdownValue} disabled={this.props.disabled} onChange={this.changeDropdownValue} name="group">
                <option value={-1}>None</option>
                <optgroup label="Ministries & Groups">{groupOptions}</optgroup>
                <optgroup label="Connect">{connectOptions}</optgroup>
            </select>
        </div>
        )
    }
}

class TagDropdown extends React.Component {
    constructor(props) {
        super(props)

        this.state = {
            dropdownValue: -1,
            newTag: false,
            customTag: ''
        }
        
        this.checkNewtag = this.checkNewtag.bind(this)
        this.handleNewtagChange = this.handleNewtagChange.bind(this)
    }

    componentDidUpdate(prevProps) {
        console.log(this.props)
        if (this.props.default != prevProps.default) {
            this.setState({
                dropdownValue: this.props.default
            })
        }
    }

    checkNewtag(e) {
        this.setState({
            newTag: e.target.value == -2,
            dropdownValue: e.target.value
        })
    }

    handleNewtagChange(e) {
        this.setState({
            customTag: e.target.value
        })

    }

    render() {
        var tagList = []
        if (this.props.tags) {
            for (const [k, v] of Object.entries(this.props.tags)) {
                tagList.push(<option value={k}>{v}</option>)
            }
        }
        
        return (<div className="tagDropdown" style={this.props.hidden? {display: "none"} : {}}>
            <label htmlFor="tag">Tag: </label>
            <select value={this.props.disabled? -1: this.state.dropdownValue} disabled={this.props.disabled} onChange={this.checkNewtag} name="tag">
                <option value={-1}>None</option>
                {tagList}
                {!this.props.noNewTags ? <option value={-2}>New Tag...</option> : ''}
            </select>
            { this.state.newTag && !this.props.disabled ? <input disabled={!this.state.newTag || this.props.disabled} onChange={this.handleNewtagChange} value={this.state.newTag? this.state.customTag : ''} type="text" name="newtag"></input> : '' }
        </div>)
    }
}