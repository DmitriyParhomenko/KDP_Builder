declare module 'fabric' {
  export const fabric: any;
  export class Canvas {
    constructor(el: any, opts?: any);
    dispose(): void;
    getZoom(): number;
    setZoom(zoom: number): void;
    zoomToPoint(point: any, zoom: number): void;
    getObjects(): any[];
    add(obj: any): void;
    remove(obj: any): void;
    clear(): void;
    renderAll(): void;
    forEachObject(cb: (obj: any) => void): void;
    moveTo(obj: any, index: number): void;
    setViewportTransform(vpt: number[]): void;
    on(event: string, handler: any): void;
    off(event: string, handler?: any): void;
    requestRenderAll(): void;
    isDragging?: boolean;
    selection?: boolean;
    defaultCursor?: string;
    hoverCursor?: string;
    width?: number;
    height?: number;
    viewportTransform?: number[];
  }
  export class Object {
    [key: string]: any;
  }
  export class Line extends Object {
    constructor(points: number[], opts?: any);
    setControlsVisibility(vis: any): void;
  }
  export class Rect extends Object {
    constructor(opts?: any);
  }
  export class Circle extends Object {
    constructor(opts?: any);
  }
  export class IText extends Object {
    constructor(text: string, opts?: any);
    setControlsVisibility(vis: any): void;
  }
  export class ActiveSelection extends Object {
    getObjects(): any[];
    calcTransformMatrix(): any;
  }
  export const util: any;
}

