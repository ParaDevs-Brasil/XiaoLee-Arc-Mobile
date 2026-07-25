import { useState, useEffect, useRef, useCallback } from 'react';
import Video from './Video';

export default function Pfp({ pfp, loop, objectPosition = "center" }: { pfp: string; loop: boolean; objectPosition?: string }) {
    const [activeSrc, setActiveSrc] = useState(pfp);
    const [pendingSrc, setPendingSrc] = useState<string | null>(null);
    const [activeVisible, setActiveVisible] = useState(true);
    const activeRef = useRef<HTMLVideoElement>(null);
    const pendingRef = useRef<HTMLVideoElement>(null);

    const swapToPending = useCallback(() => {
        if (!pendingSrc) return;
        // Fade: active → out, pending → in
        setActiveVisible(false);
        setTimeout(() => {
            setActiveSrc(pendingSrc);
            setPendingSrc(null);
            setActiveVisible(true);
        }, 250);
    }, [pendingSrc]);

    // Queue the next src when Video service changes it
    useEffect(() => {
        const unsubscribe = Video.subscribe((newPfp) => {
            if (newPfp !== activeSrc) {
                setPendingSrc(newPfp);
            }
        });
        return unsubscribe;
    }, [activeSrc]);

    // Sync with parent prop changes
    useEffect(() => {
        if (pfp !== activeSrc && pfp !== pendingSrc) {
            setPendingSrc(pfp);
        }
    }, [pfp, activeSrc, pendingSrc]);

    const handleActiveEnded = () => {
        if (!loop) Video.primaryVideoDidEnd();
    };

    if (!activeSrc || activeSrc === "null" || activeSrc === "undefined") {
        return (
            <div className="w-16 h-16 rounded-full bg-gradient-to-br from-[var(--pfp-fallback-bg-start)] to-[var(--pfp-fallback-bg-end)] flex items-center justify-center border-2 border-[var(--pfp-fallback-border)]">
                <span className="text-[var(--pfp-fallback-icon)] text-xs">✨</span>
            </div>
        );
    }

    return (
        <div className="absolute inset-0 w-full h-full">
            {/* Active video — stays visible until swap completes */}
            <video
                ref={activeRef}
                src={`/${activeSrc}`}
                className="absolute inset-0 w-full h-full object-cover rounded-[calc(1.5rem-4px)] transition-opacity duration-250"
                style={{ opacity: activeVisible ? 1 : 0, objectPosition }}
                autoPlay
                muted
                playsInline
                loop={loop}
                onEnded={handleActiveEnded}
            />

            {/* Pending video — preloads silently, triggers swap when ready */}
            {pendingSrc && (
                <video
                    ref={pendingRef}
                    src={`/${pendingSrc}`}
                    className="absolute inset-0 w-full h-full object-cover rounded-[calc(1.5rem-4px)]"
                    style={{ opacity: 0, objectPosition }}
                    autoPlay
                    muted
                    playsInline
                    preload="auto"
                    onCanPlay={swapToPending}
                />
            )}
        </div>
    );
}
