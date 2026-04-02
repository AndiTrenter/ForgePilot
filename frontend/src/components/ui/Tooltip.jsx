import React, { useState, useRef } from 'react';

/**
 * Tooltip Component
 * Zeigt Tooltips nach 2 Sekunden Hover an
 */

const Tooltip = ({ children, text, position = "bottom" }) => {
  const [show, setShow] = useState(false);
  const timeoutRef = useRef(null);
  
  const handleMouseEnter = () => {
    timeoutRef.current = setTimeout(() => setShow(true), 2000); // 2 seconds delay
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
        <div className={`absolute ${positionClasses[position]} z-[100] pointer-events-none`}>
          <div className="bg-zinc-800 text-white text-xs px-3 py-2 rounded-lg shadow-xl border border-zinc-700 whitespace-nowrap max-w-xs">
            {text}
          </div>
        </div>
      )}
    </div>
  );
};

export default Tooltip;
