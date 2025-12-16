"use client";

import { useState, FormEvent } from "react";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";

interface ChatInputProps {
  onSend: (content: string) => void;
  isLoading?: boolean;
}

export function ChatInput({ onSend, isLoading }: ChatInputProps) {
  const [content, setContent] = useState("");

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!content.trim() || isLoading) return;
    onSend(content);
    setContent("");
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-3">
      <Input
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="メッセージを入力..."
        disabled={isLoading}
      />
      <Button type="submit" disabled={!content.trim() || isLoading}>
        {isLoading ? "送信中..." : "送信"}
      </Button>
    </form>
  );
}


