import AdminPanel from './admin.jsx'
import LoginButton from './login.jsx'
import BulletinList from './bulletin.jsx'
import GalleryList from './gallery.jsx'
import NewsDropdowns from './news.jsx'

const components = {
    'loginButton': <LoginButton/>,
    'bulletinList': <BulletinList/>,
    'adminPanel': <AdminPanel/>,
    'galleryList': <GalleryList/>,
    'newsDropdowns': <NewsDropdowns/>,
    'newsDropdownsTagless': <NewsDropdowns noNewTags={true}/>
}

for (var c in components) {
    if (document.getElementById(c) != null) {
        ReactDOM.render(
            components[c],
            document.getElementById(c)
        )
    }
}