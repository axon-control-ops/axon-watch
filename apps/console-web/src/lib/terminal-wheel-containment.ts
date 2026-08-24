interface TerminalWheelEventLike {
  target: EventTarget | null;
  stopPropagation: () => void;
}

function closestTerminalElement(target: EventTarget | null): Element | null {
  if (!target || typeof (target as Element).closest !== 'function') {
    return null;
  }
  return (target as Element).closest(
    '.xterm, .xterm-viewport, .xterm-screen, .xterm-helpers',
  );
}

export function containTerminalWheelEvent(event: TerminalWheelEventLike): boolean {
  if (!closestTerminalElement(event.target)) {
    return false;
  }

  event.stopPropagation();
  return true;
}

export function attachTerminalWheelContainment(container: HTMLElement): () => void {
  const handleWheel = (event: WheelEvent): void => {
    containTerminalWheelEvent(event);
  };

  container.addEventListener('wheel', handleWheel, { passive: true });
  return () => {
    container.removeEventListener('wheel', handleWheel);
  };
}
