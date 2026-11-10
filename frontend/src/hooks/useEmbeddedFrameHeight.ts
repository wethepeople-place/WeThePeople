import { useEffect, type RefObject } from 'react';

export default function useEmbeddedFrameHeight(
  isEmbedded: boolean,
  frame: 'elections' | 'representatives',
  contentRef: RefObject<HTMLElement | null>,
) {
  useEffect(() => {
    if (!isEmbedded || !contentRef.current) return;

    const content = contentRef.current;
    let animationFrame = 0;
    const reportHeight = () => {
      cancelAnimationFrame(animationFrame);
      animationFrame = requestAnimationFrame(() => {
        const height = Math.ceil(content.getBoundingClientRect().height);
        if (height > 0) {
          window.parent.postMessage({ type: 'wtp:act-frame-height', frame, height }, window.location.origin);
        }
      });
    };

    reportHeight();
    const resizeObserver = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(reportHeight);
    resizeObserver?.observe(content);
    const mutationObserver = new MutationObserver(reportHeight);
    mutationObserver.observe(content, { childList: true, subtree: true, characterData: true, attributes: true });
    window.addEventListener('resize', reportHeight);

    return () => {
      cancelAnimationFrame(animationFrame);
      resizeObserver?.disconnect();
      mutationObserver.disconnect();
      window.removeEventListener('resize', reportHeight);
    };
  }, [contentRef, frame, isEmbedded]);
}
