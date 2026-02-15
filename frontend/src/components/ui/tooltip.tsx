import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * TooltipProvider is a passthrough wrapper for API compatibility.
 * No context is needed since tooltips are CSS-only (group-hover).
 */
function TooltipProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
TooltipProvider.displayName = "TooltipProvider";

/**
 * Tooltip is a wrapper that establishes a positioning context
 * and a Tailwind "group" scope for hover-triggered visibility.
 */
const Tooltip = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("group/tooltip relative inline-flex", className)}
    {...props}
  />
));
Tooltip.displayName = "Tooltip";

/**
 * TooltipTrigger renders the element that, when hovered,
 * shows the tooltip content via the group-hover mechanism.
 */
const TooltipTrigger = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement>
>(({ className, ...props }, ref) => (
  <button
    ref={ref}
    type="button"
    className={cn("inline-flex", className)}
    {...props}
  />
));
TooltipTrigger.displayName = "TooltipTrigger";

type TooltipSide = "top" | "bottom" | "left" | "right";

interface TooltipContentProps extends React.HTMLAttributes<HTMLDivElement> {
  side?: TooltipSide;
  sideOffset?: number;
}

/**
 * TooltipContent renders the tooltip popup.
 * It uses CSS-only visibility via group-hover and absolute positioning.
 */
const TooltipContent = React.forwardRef<HTMLDivElement, TooltipContentProps>(
  ({ className, side = "top", sideOffset = 4, style, ...props }, ref) => {
    const sideClasses: Record<TooltipSide, string> = {
      top: "bottom-full left-1/2 -translate-x-1/2 mb-[var(--offset)]",
      bottom: "top-full left-1/2 -translate-x-1/2 mt-[var(--offset)]",
      left: "right-full top-1/2 -translate-y-1/2 mr-[var(--offset)]",
      right: "left-full top-1/2 -translate-y-1/2 ml-[var(--offset)]",
    };

    return (
      <div
        ref={ref}
        role="tooltip"
        style={
          {
            "--offset": `${sideOffset}px`,
            ...style,
          } as React.CSSProperties
        }
        className={cn(
          "pointer-events-none absolute z-50 w-max max-w-xs rounded-[var(--radius)] border border-[var(--border)] bg-[var(--popover)] px-3 py-1.5 text-sm text-[var(--popover-foreground)] shadow-md",
          "invisible opacity-0 group-hover/tooltip:visible group-hover/tooltip:opacity-100",
          "transition-opacity duration-150",
          sideClasses[side],
          className
        )}
        {...props}
      />
    );
  }
);
TooltipContent.displayName = "TooltipContent";

export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider };
