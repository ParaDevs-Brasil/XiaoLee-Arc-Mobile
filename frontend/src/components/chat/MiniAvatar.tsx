import React, { useState, useEffect } from "react";
import Pfp from "../Pfp";
import Video from "../Video";

/**
 * Compact live avatar for the chat header on small screens,
 * where the AnimePanel side card is hidden. Subscribes to the
 * same Video service, so reactions and idle expressions play here too.
 */
export default function MiniAvatar({ size = 40 }: { size?: number }) {
  const [currentPfp, setCurrentPfp] = useState(Video.getPfp());
  const [shouldLoop, setShouldLoop] = useState(false);

  useEffect(() => {
    const unsubscribe = Video.subscribe((newPfp, loop) => {
      setCurrentPfp(newPfp);
      setShouldLoop(loop);
    });
    return unsubscribe;
  }, []);

  return (
    <span
      className="relative block shrink-0 overflow-hidden rounded-full ring-2 ring-white shadow-md bg-[var(--accent-soft)]"
      style={{ width: size, height: size }}
    >
      {/* Zoom toward the face — source videos frame the full upper body */}
      <span
        className="absolute inset-0"
        style={{ transform: "scale(1.9)", transformOrigin: "50% 18%" }}
      >
        <Pfp pfp={currentPfp} loop={shouldLoop} />
      </span>
    </span>
  );
}
