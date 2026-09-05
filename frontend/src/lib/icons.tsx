"use client";
import React from "react";

type IconProps = React.SVGProps<SVGSVGElement> & { size?: number };

function Svg({ size = 16, children, ...props }: IconProps & { children: React.ReactNode }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" {...props}>{children}</svg>;
}
export const LayoutGrid = (p: IconProps) => <Svg {...p}><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></Svg>;
export const Radar = (p: IconProps) => <Svg {...p}><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3" /></Svg>;
export const Route = (p: IconProps) => <Svg {...p}><circle cx="6" cy="6" r="2.5" /><circle cx="18" cy="18" r="2.5" /><path d="M8 8c2 1.5 6 4 8 8" /><circle cx="12" cy="12" r="1" fill="currentColor" /></Svg>;
export const ShieldCheck = (p: IconProps) => <Svg {...p}><path d="M12 2 17 5v5c0 3-2 6-5 7-3-1-5-4-5-7V5z" /><path d="M9 12l2 2 4-5" /></Svg>;
export const Layers = (p: IconProps) => <Svg {...p}><path d="M12 2 2.5 7.5 12 13 21.5 7.5z" /><path d="M2.5 12 12 17.5 21.5 12" /><path d="M2.5 17 12 22 21.5 17" opacity={0.6} /></Svg>;
export const BarChart3 = (p: IconProps) => <Svg {...p}><path d="M3 12h4v9H3zM10 7h4v14h-4zM17 2h4v19h-4z" /></Svg>;
export const FlaskConical = (p: IconProps) => <Svg {...p}><path d="M10 2h4v6l4 6c1 1.5 0 3.5-2 3.5H8c-2 0-3-2-2-3.5l4-6z" /><path d="M8 14h8" opacity={0.6} /></Svg>;
export const Coins = (p: IconProps) => <Svg {...p}><ellipse cx="12" cy="6" rx="8" ry="3.5" /><path d="M4 6v8c0 2 3.5 3.5 8 3.5s8-1.5 8-3.5V6" /><ellipse cx="12" cy="14" rx="8" ry="3.5" /></Svg>;
export const BookOpen = (p: IconProps) => <Svg {...p}><path d="M2 7c2-1 4-1.5 6-1.5S12 6 14 7v10c-2-1-4-1.5-6-1.5S4 16 2 17z" /><path d="M14 7c2-1 4-1.5 6-1.5S22 6 22 7v10c-2-1-4-1.5-6-1.5S12 16 14 17z" /></Svg>;
export const SlidersHorizontal = (p: IconProps) => <Svg {...p}><path d="M3 6h10M14 6h7" /><circle cx="12" cy="6" r="2.5" fill="white" /><path d="M3 18h16M21 18h1" /><circle cx="17" cy="18" r="2.5" fill="white" /></Svg>;
export const ScrollText = (p: IconProps) => <Svg {...p}><path d="M8 2h7c1 0 1 .5 1 1.5v14c0 1-1 1.5-1 1.5H8c-1 0-1-.5-1-1.5V3.5C7 2.5 8 2 8 2z" /><path d="M9 8h6M9 12h6M9 16h4" /></Svg>;
export const Sparkles = (p: IconProps) => <Svg {...p}><path d="M12 2l1.2 4.8L18 8l-4.8 1.2L12 14l-1.2-4.8L6 8l4.8-1.2z" /><path d="M19 11l.8 2.2L22 14l-2.2.8L19 17l-.8-2.2L16 14l2.2-.8z" /><path d="M5 15l.8 2.2L8 18l-2.2.8L5 21l-.8-2.2L2 18l2.2-.8z" /></Svg>;
export const Zap = (p: IconProps) => <Svg {...p}><path d="M13 2L3 14h7l-1 8 10-16h-7l1-4z" /></Svg>;
export const ShieldAlert = (p: IconProps) => <Svg {...p}><path d="M12 2 17 5v5c0 3-2 6-5 7-3-1-5-4-5-7V5z" /><path d="M12 8v5M12 16h.01" /></Svg>;
export const Timer = (p: IconProps) => <Svg {...p}><circle cx="12" cy="12" r="8" /><path d="M12 8v4l3 2" /></Svg>;
export const Wallet = (p: IconProps) => <Svg {...p}><path d="M3 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><path d="M16 12h4" /></Svg>;
export const TrendingUp = (p: IconProps) => <Svg {...p}><path d="M3 17l6-6 4 4 8-8" /><path d="M14 7h7v7" /></Svg>;
export const AlertTriangle = (p: IconProps) => <Svg {...p}><path d="M12 3L2 20h20L12 3z" /><path d="M12 9v6M12 17h.01" /></Svg>;
export const Check = (p: IconProps) => <Svg {...p}><path d="M5 13l4 4L19 7" /></Svg>;
export const X = (p: IconProps) => <Svg {...p}><path d="M6 6l12 12M18 6L6 18" /></Svg>;
export const ArrowRight = (p: IconProps) => <Svg {...p}><path d="M5 12h14M13 6l6 6-6 6" /></Svg>;
export const Activity = (p: IconProps) => <Svg {...p}><path d="M22 12h-4l-3 9L9 3l-3 9H2" /></Svg>;
export const Globe = (p: IconProps) => <Svg {...p}><circle cx="12" cy="12" r="10" /><path d="M2 12h20M12 2a15 15 0 0 1 0 20M12 2a15 15 0 0 0 0 20" /></Svg>;
export const Menu = (p: IconProps) => <Svg {...p}><path d="M4 6h16M4 12h16M4 18h16" /></Svg>;
export const Sun = (p: IconProps) => <Svg {...p}><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></Svg>;
export const Moon = (p: IconProps) => <Svg {...p}><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" /></Svg>;
export const ExternalLink = (p: IconProps) => <Svg {...p}><path d="M15 3h6v6" /><path d="M9 15L21 3" /><path d="M15 15H9a2 2 0 0 1-2-2V9" /></Svg>;
