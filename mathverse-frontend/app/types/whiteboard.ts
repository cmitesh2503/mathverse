export type WhiteboardGraph = {
  x_min: number;
  x_max: number;
  y_min: number;
  y_max: number;
  lines?: Array<{
    label?: string;
    color?: string;
    points: Array<[number, number]>;
  }>;
  points?: Array<{
    x: number;
    y: number;
    label?: string;
    color?: string;
  }>;
};

export type WhiteboardPayload = {
  title?: string;
  subtitle?: string;
  chalk_lines?: string[];
  equations?: string[];
  problem?: string;
  graph?: WhiteboardGraph;
};
