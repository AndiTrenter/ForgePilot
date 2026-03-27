import React, { useState, useRef } from "react";
import { Loader2 } from "lucide-react";

// ============== Constants ==============
export const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

// ============== Tooltip Component ==============
export const Tooltip = ({ children, text, position = "bottom" }) => {
  const [show, setShow] = useState(false);
  const timeoutRef = useRef(null);
  
  const handleMouseEnter = () => {
    timeoutRef.current = setTimeout(() => setShow(true), 2000);
  };
  
  const handleMouseLeave = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setShow(false);
  };
  
  const handleClick = () => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    setShow(false);
  };

  const positionClasses = {
    top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
    bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
    left: "right-full top-1/2 -translate-y-1/2 mr-2",
    right: "left-full top-1/2 -translate-y-1/2 ml-2",
  };

  return (
    <div 
      className="relative inline-flex"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={handleClick}
    >
      {children}
      {show && (
        <div className={`absolute z-[100] ${positionClasses[position]} animate-fade-in`}>
          <div className="bg-zinc-800 border border-zinc-700 text-zinc-200 text-xs px-3 py-2 rounded-lg shadow-xl max-w-xs whitespace-normal">
            {text}
          </div>
        </div>
      )}
    </div>
  );
};

// ============== Logo Component ==============
export const Logo = () => (
  <div className="font-mono font-bold text-lg tracking-tight flex items-center gap-2">
    <div className="w-6 h-6 bg-white rounded-sm flex items-center justify-center">
      <span className="text-black text-sm font-bold">F</span>
    </div>
    <span>ForgePilot</span>
  </div>
);

// ============== Loading Screen ==============
export const LoadingScreen = () => (
  <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
    <Loader2 size={32} className="animate-spin text-zinc-500" />
  </div>
);
