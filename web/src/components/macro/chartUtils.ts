/**
 * Shared chart utilities and constants for macro dashboard components.
 */

export const CHART_COLORS = [
  '#3498db', '#2ecc71', '#e74c3c', '#f39c12',
  '#9b59b6', '#1abc9c', '#e67e22', '#34495e',
  '#c0392b', '#27ae60',
];

export const getColor = (index: number): string => 
  CHART_COLORS[index % CHART_COLORS.length];
