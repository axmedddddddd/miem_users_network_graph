import React from "react";
import ReactDOM from "react-dom";

import "./styles.css";
import Root from "./views/Root";

let render = () => {
    ReactDOM.render(
        <React.StrictMode>
            <Root/>
        </React.StrictMode>,
        document.getElementById("root"),
    );
}

export let observer = () => {
    render();
    console.log('rend')
}

observer()