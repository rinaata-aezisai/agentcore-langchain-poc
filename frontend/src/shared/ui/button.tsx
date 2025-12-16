"use client";

import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { ButtonHTMLAttributes, forwardRef } from "react";

type ButtonVariant = "primary" | "secondary" | "ghost";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variants: Record<ButtonVariant, string> = {
  primary: "bg-primary-600 text-white hover:bg-primary-700",
  secondary: "bg-slate-700 text-white hover:bg-slate-600",
  ghost: "bg-transparent text-slate-300 hover:bg-slate-800",
};

const sizes: Record<ButtonSize, string> = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-base",
  lg: "px-6 py-3 text-lg",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", disabled, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={twMerge(
          clsx(
            "rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500",
            variants[variant],
            sizes[size],
            disabled && "opacity-50 cursor-not-allowed",
            className
          )
        )}
        disabled={disabled}
        {...props}
      />
    );
  }
);

Button.displayName = "Button";


