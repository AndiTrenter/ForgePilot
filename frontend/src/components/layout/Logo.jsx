import React from 'react';

/**
 * Logo Component
 * ForgePilot Logo mit Icon und Text
 */

const Logo = () => {
  return (
    <div className="flex items-center gap-2">
      <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
        <span className="text-white text-lg font-bold">F</span>
      </div>
      <span className="font-bold text-lg text-white">ForgePilot</span>
    </div>
  );
};

export default Logo;
