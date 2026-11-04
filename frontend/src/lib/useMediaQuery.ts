"use client";

import { useEffect, useState } from "react";

/** True while the media query matches. False during SSR / first paint, then updates. */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);
  useEffect(() => {
    const mql = window.matchMedia(query);
    const update = () => setMatches(mql.matches);
    update();
    mql.addEventListener("change", update);
    return () => mql.removeEventListener("change", update);
  }, [query]);
  return matches;
}

/** Phones (below Tailwind's sm breakpoint). */
export const useIsPhone = () => useMediaQuery("(max-width: 639px)");
