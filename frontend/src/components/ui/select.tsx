"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface SelectContextValue {
  value: string;
  onValueChange: (value: string) => void;
}

const SelectContext = React.createContext<SelectContextValue | undefined>(undefined);

function useSelectContext() {
  const context = React.useContext(SelectContext);
  if (!context) {
    throw new Error("Select compound components must be used within a <Select> component.");
  }
  return context;
}

interface SelectProps {
  children: React.ReactNode;
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
}

function Select({
  children,
  value: controlledValue,
  defaultValue = "",
  onValueChange,
}: SelectProps) {
  const [internalValue, setInternalValue] = React.useState(defaultValue);

  const isControlled = controlledValue !== undefined;
  const value = isControlled ? controlledValue : internalValue;

  const handleValueChange = React.useCallback(
    (newValue: string) => {
      if (!isControlled) {
        setInternalValue(newValue);
      }
      onValueChange?.(newValue);
    },
    [isControlled, onValueChange]
  );

  return (
    <SelectContext.Provider value={{ value, onValueChange: handleValueChange }}>
      {children}
    </SelectContext.Provider>
  );
}
Select.displayName = "Select";

interface SelectTriggerProps extends React.HTMLAttributes<HTMLDivElement> {
  children?: React.ReactNode;
}

const SelectTrigger = React.forwardRef<HTMLDivElement, SelectTriggerProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "relative flex h-10 w-full items-center justify-between rounded-[var(--radius)] border border-[var(--input)] bg-[var(--background)] px-3 py-2 text-sm ring-offset-[var(--background)] focus-within:outline-none focus-within:ring-2 focus-within:ring-[var(--ring)] focus-within:ring-offset-2 [&>span]:line-clamp-1",
          className
        )}
        {...props}
      >
        {children}
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="ml-2 shrink-0 opacity-50"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </div>
    );
  }
);
SelectTrigger.displayName = "SelectTrigger";

function SelectValue({ placeholder }: { placeholder?: string }) {
  const { value } = useSelectContext();
  return <span>{value || placeholder || ""}</span>;
}
SelectValue.displayName = "SelectValue";

interface SelectContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

function SelectContent({ className, children, ...props }: SelectContentProps) {
  const { value, onValueChange } = useSelectContext();

  // Collect items from children and build a native select
  const items: Array<{ value: string; label: string; disabled?: boolean }> = [];

  React.Children.forEach(children, (child) => {
    if (React.isValidElement<SelectItemProps>(child) && child.type === SelectItem) {
      items.push({
        value: child.props.value,
        label: typeof child.props.children === "string" ? child.props.children : child.props.value,
        disabled: child.props.disabled,
      });
    }
  });

  return (
    <select
      className={cn(
        "absolute inset-0 h-full w-full cursor-pointer opacity-0",
        className
      )}
      value={value}
      onChange={(e) => onValueChange(e.target.value)}
      {...(props as React.SelectHTMLAttributes<HTMLSelectElement>)}
    >
      {items.map((item) => (
        <option key={item.value} value={item.value} disabled={item.disabled}>
          {item.label}
        </option>
      ))}
    </select>
  );
}
SelectContent.displayName = "SelectContent";

interface SelectItemProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string;
  disabled?: boolean;
  children: React.ReactNode;
}

function SelectItem({ value, disabled, children, ...props }: SelectItemProps) {
  // This component is used declaratively to define options.
  // It does not render DOM directly; SelectContent reads its props.
  return null;
}
SelectItem.displayName = "SelectItem";

// Wrapper that combines trigger + native select for proper layering
interface SelectWrapperProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

/**
 * Usage example:
 *
 * <Select value={val} onValueChange={setVal}>
 *   <SelectTrigger>
 *     <SelectValue placeholder="Pick one" />
 *     <SelectContent>
 *       <SelectItem value="a">Option A</SelectItem>
 *       <SelectItem value="b">Option B</SelectItem>
 *     </SelectContent>
 *   </SelectTrigger>
 * </Select>
 *
 * The SelectContent renders an invisible native <select> overlaying the trigger,
 * so the browser handles the dropdown while the trigger displays the styled value.
 */

export {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
};
