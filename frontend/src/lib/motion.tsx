"use client";
import React from "react";
type Props = React.HTMLAttributes<HTMLDivElement> & { delay?: number };
export function MotionDiv({ delay = 0, className, children, ...props }: Props) {
  return <div className={className} style={{ animation: `rise 0.55s cubic-bezier(0.16,1,0.3,1) both`, animationDelay: `${delay}ms`, ...props.style }} {...props}>{children}</div>;
}
export function MotionFade({ delay = 0, className, children, ...props }: Props) {
  return <div className={className} style={{ animation: `fade 0.4s ease both`, animationDelay: `${delay}ms`, ...props.style }} {...props}>{children}</div>;
}
