"use client";

import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { InputHTMLAttributes, forwardRef } from "react";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={twMerge(
          clsx(
            "w-full rounded-lg border border-slate-600 bg-slate-800 px-4 py-2",
            "text-white placeholder-slate-400",
            "focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20",
            "transition-colors",
            className
          )
        )}
        {...props}
      />
    );
  }
);

Input.displayName = "Input";



