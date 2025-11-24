import React, { component } from "react";
import "./Loader.css";
// import loadingGif from "../Assets/loading.gif";

const Loader = () => {
  return (
    <div className="center">
      <div className="text-loader">
        <span>
          {/* <img
            width={100}
            src={loadingGif}
            alt="loading..." className="opacity-[0.25]"
          /> */}
        </span>
        <div className="text-container">
          <span className="letter">S</span>
          <span className="letter">A</span>
          <span className="letter">M</span>
          <span className="letter">R</span>
          <span className="letter">I</span>
          <span className="letter">D</span>
          <span className="letter">D</span>
          <span className="letter">H</span>
          <span className="letter">I</span>
        </div>
      </div>
    </div>
  );
};

export default Loader;