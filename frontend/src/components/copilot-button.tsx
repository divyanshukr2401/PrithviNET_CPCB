"use client";

import { Sparkles } from "lucide-react";

interface CopilotButtonProps {
  onClick: () => void;
  isOpen: boolean;
}

export function CopilotButton({ onClick, isOpen }: CopilotButtonProps) {
  if (isOpen) return null;

  return (
    <button
      onClick={onClick}
      className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-full bg-gradient-to-r from-emerald-600 to-blue-600 text-white shadow-lg hover:shadow-xl hover:scale-105 transition-all duration-200 group"
      title="Ask Smart Co-pilot"
    >
      <Sparkles className="w-5 h-5 group-hover:animate-pulse" />
      <span className="text-sm font-medium hidden sm:inline">
        Ask Smart Co-pilot
      </span>
    </button>
  );
}
