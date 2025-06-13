/**
 * Navigation key literals
 */
export type NavigationKey = 'pagedown' | 'pageup' | 'home' | 'end' | 'left' | 'right' | 'up' | 'down';

/**
 * Special key literals
 */
export type SpecialKey = 'enter' | 'esc' | 'tab' | 'space' | 'backspace' | 'del';

/**
 * Modifier key literals
 */
export type ModifierKey = 'ctrl' | 'alt' | 'shift' | 'win' | 'command' | 'option';

/**
 * Function key literals
 */
export type FunctionKey = 'f1' | 'f2' | 'f3' | 'f4' | 'f5' | 'f6' | 'f7' | 'f8' | 'f9' | 'f10' | 'f11' | 'f12';

/**
 * Keyboard keys that can be used with press_key.
 */
export enum Key {
  // Navigation
  PAGE_DOWN = 'pagedown',
  PAGE_UP = 'pageup',
  HOME = 'home',
  END = 'end',
  LEFT = 'left',
  RIGHT = 'right',
  UP = 'up',
  DOWN = 'down',
  
  // Special keys
  RETURN = 'enter',
  ENTER = 'enter',
  ESCAPE = 'esc',
  ESC = 'esc',
  TAB = 'tab',
  SPACE = 'space',
  BACKSPACE = 'backspace',
  DELETE = 'del',
  
  // Modifier keys
  ALT = 'alt',
  CTRL = 'ctrl',
  SHIFT = 'shift',
  WIN = 'win',
  COMMAND = 'command',
  OPTION = 'option',
  
  // Function keys
  F1 = 'f1',
  F2 = 'f2',
  F3 = 'f3',
  F4 = 'f4',
  F5 = 'f5',
  F6 = 'f6',
  F7 = 'f7',
  F8 = 'f8',
  F9 = 'f9',
  F10 = 'f10',
  F11 = 'f11',
  F12 = 'f12'
}

/**
 * Combined key type
 */
export type KeyType = Key | NavigationKey | SpecialKey | ModifierKey | FunctionKey | string;

/**
 * Key type for mouse actions
 */
export type MouseButton = 'left' | 'right' | 'middle';

/**
 * Information about a window in the accessibility tree.
 */
export interface AccessibilityWindow {
  app_name: string;
  pid: number;
  frontmost: boolean;
  has_windows: boolean;
  windows: Array<Record<string, any>>;
}

/**
 * Complete accessibility tree information.
 */
export interface AccessibilityTree {
  success: boolean;
  frontmost_application: string;
  windows: AccessibilityWindow[];
}
