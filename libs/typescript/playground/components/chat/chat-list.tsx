import { Message, useChat } from "ai/react";
import React, { useRef, useEffect } from "react";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback, AvatarImage } from "../ui/avatar";
import { ChatProps } from "./chat";
import Image from "next/image";
import CodeDisplayBlock from "../code-display-block";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { INITIAL_QUESTIONS } from "@/utils/initial-questions";
import { Button } from "../ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card";
import { Brain, ChevronDown, ChevronRight, Clock, Loader, Camera } from "lucide-react";

// Component to render tool invocations
function ToolInvocation({ invocation }: { invocation: any }) {
  const [isExpanded, setIsExpanded] = React.useState(false);
  
  if (invocation.toolName === 'computer_action') {
    return (
      <Card className="my-1 border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950">
        <CardHeader 
          className="pb-1 pt-2 px-3 cursor-pointer hover:bg-blue-100 dark:hover:bg-blue-900 transition-colors"
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <CardTitle className="text-xs font-medium text-blue-800 dark:text-blue-200 flex items-center gap-1">
            {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            {invocation.result?.title || '🛠️ Computer Action'}
          </CardTitle>
        </CardHeader>
        {isExpanded && (
          <CardContent className="pt-0 px-3 pb-2">
            <pre className="text-xs bg-gray-100 dark:bg-gray-800 p-2 rounded overflow-x-auto">
              <code>{JSON.stringify(invocation.args, null, 2)}</code>
            </pre>
          </CardContent>
        )}
      </Card>
    );
  }
  
  // Default rendering for other tool types
  return (
    <Card className="my-1 border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-900">
      <CardHeader 
        className="pb-1 pt-2 px-3 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <CardTitle className="text-xs font-medium flex items-center gap-1">
          {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          Tool: {invocation.toolName}
        </CardTitle>
      </CardHeader>
      {isExpanded && (
        <CardContent className="pt-0 px-3 pb-2">
          <pre className="text-xs bg-gray-100 dark:bg-gray-800 p-2 rounded overflow-x-auto">
            <code>{JSON.stringify(invocation.args, null, 2)}</code>
          </pre>
        </CardContent>
      )}
    </Card>
  );
}

// Component to render reasoning annotations
function ReasoningAnnotation({ annotations }: { annotations: any[] }) {
  const [isExpanded, setIsExpanded] = React.useState(false);
  
  const reasoningAnnotations = annotations.filter(ann => ann.type === 'reasoning');
  if (reasoningAnnotations.length === 0) return null;
  
  const totalReasoningTime = reasoningAnnotations.length * 2; // Approximate 2 seconds per reasoning step
  
  return (
    <div>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <Brain size={16} />
        <span>Thought for {totalReasoningTime}s</span>
        {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </button>
      {isExpanded && (
        <div className="mt-2 space-y-1">
          {reasoningAnnotations.map((annotation, index) => (
            <div key={index} className="text-xs text-muted-foreground p-2 rounded border">
              <div className="whitespace-pre-wrap">{annotation.content}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// Component to render screenshot annotations
function ScreenshotAnnotation({ annotations }: { annotations: any[] }) {
  const [isExpanded, setIsExpanded] = React.useState(false);
  
  const screenshotAnnotations = annotations.filter(ann => ann.type === 'screenshot');
  if (screenshotAnnotations.length === 0) return null;
  
  return (
    <div>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        <Camera size={16} />
        <span>Screenshot{screenshotAnnotations.length > 1 ? 's' : ''}</span>
        {isExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </button>
      {isExpanded && (
        <div className="mt-2 space-y-2">
          {screenshotAnnotations.map((annotation, index) => (
            <div key={index} className="border rounded p-2">
              {annotation.action_type && (
                <div className="text-xs text-muted-foreground mb-2">
                  Action: {annotation.action_type}
                </div>
              )}
              <img 
                src={`data:image/png;base64,${annotation.screenshot_base64}`}
                alt={`Screenshot ${annotation.action_type ? `after ${annotation.action_type}` : ''}`}
                className="max-w-full h-auto rounded border"
                style={{ maxHeight: '300px' }}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ChatList({
  messages,
  input,
  handleInputChange,
  handleSubmit,
  isLoading,
  error,
  stop,
  loadingSubmit,
  formRef,
  isMobile,
}: ChatProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const [name, setName] = React.useState<string>("");
  const [localStorageIsLoading, setLocalStorageIsLoading] =
    React.useState(true);
  const [initialQuestions, setInitialQuestions] = React.useState<Message[]>([]);

  const scrollToBottom = () => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const username = localStorage.getItem("ollama_user");
    if (username) {
      setName(username);
      setLocalStorageIsLoading(false);
    }
  }, []);

  useEffect(() => {
    // Fetch 4 initial questions
    if (messages.length === 0) {
      const questionCount = isMobile ? 2 : 4;

      setInitialQuestions(
        INITIAL_QUESTIONS.sort(() => Math.random() - 0.5)
          .slice(0, questionCount)
          .map((message) => {
            return {
              id: "1",
              role: "user",
              content: message.content,
            };
          })
      );
    }
  }, [isMobile]);

  const onClickQuestion = (value: string, e: React.MouseEvent) => {
    e.preventDefault();

    handleInputChange({
      target: { value },
    } as React.ChangeEvent<HTMLTextAreaElement>);

    setTimeout(() => {
      formRef.current?.dispatchEvent(
        new Event("submit", {
          cancelable: true,
          bubbles: true,
        })
      );
    }, 1);
  };

  messages.map((m) => console.log(m.experimental_attachments))

  if (messages.length === 0) {
    return (
      <div className="w-full h-full flex justify-center items-center">
        <div className="relative flex flex-col gap-4 items-center justify-center w-full h-full">
          <div></div>
          <div className="flex flex-col gap-4 items-center">
            <Image
              src="/logo-black.svg"
              alt="AI"
              width={60}
              height={60}
              className="h-20 w-14 object-contain dark:invert"
            />
            <p className="text-center text-lg text-muted-foreground">
              How can I help you today?
            </p>
          </div>

          <div className="absolute bottom-0 w-full px-4 sm:max-w-3xl grid gap-2 sm:grid-cols-2 sm:gap-4 text-sm">
            {/* Only display 4 random questions */}
            {initialQuestions.length > 0 &&
              initialQuestions.map((message) => {
                const delay = Math.random() * 0.25;

                return (
                  <motion.div
                    initial={{ opacity: 0, scale: 1, y: 10, x: 0 }}
                    animate={{ opacity: 1, scale: 1, y: 0, x: 0 }}
                    exit={{ opacity: 0, scale: 1, y: 10, x: 0 }}
                    transition={{
                      opacity: { duration: 0.1, delay },
                      scale: { duration: 0.1, delay },
                      y: { type: "spring", stiffness: 100, damping: 10, delay },
                    }}
                    key={message.content}
                  >
                    <Button
                      key={message.content}
                      type="button"
                      variant="outline"
                      className="sm:text-start px-4 py-8 flex w-full justify-center sm:justify-start items-center text-sm whitespace-pre-wrap"
                      onClick={(e) => onClickQuestion(message.content, e)}
                    >
                      {message.content}
                    </Button>
                  </motion.div>
                );
              })}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      id="scroller"
      className="w-full overflow-y-scroll overflow-x-hidden h-full justify-end"
    >
      <div className="w-full flex flex-col overflow-x-hidden overflow-y-hidden min-h-full justify-end">
        {messages.map((message, index) => (
          <motion.div
            key={index}
            layout
            initial={{ opacity: 0, scale: 1, y: 20, x: 0 }}
            animate={{ opacity: 1, scale: 1, y: 0, x: 0 }}
            exit={{ opacity: 0, scale: 1, y: 20, x: 0 }}
            transition={{
              opacity: { duration: 0.1 },
              layout: {
                type: "spring",
                bounce: 0.3,
                duration: messages.indexOf(message) * 0.05 + 0.2,
              },
            }}
            className={cn(
              "flex flex-col gap-2 p-4 whitespace-pre-wrap",
              message.role === "user" ? "items-end" : "items-start"
            )}
          >
            <div className="flex gap-3 items-center">
              {message.role === "user" && (
                <div className="flex items-end gap-3">
                  <div className="flex flex-col gap-2 bg-accent p-3 rounded-md max-w-xs sm:max-w-2xl overflow-x-auto">
                    <div className="flex gap-2">
                    {message.experimental_attachments?.filter(attachment => attachment.contentType?.startsWith('image/'),).map((attachment, index) => (
                      <Image
                      key={`${message.id}-${index}`}
                      src={attachment.url}
                      width={200}
                      height={200} alt='attached image'
                      className="rounded-md object-contain"                
                      />
                    ))}
                    </div>
                    <p className="text-end">{message.content}</p>
                  </div>
                  <Avatar className="flex justify-start items-center overflow-hidden">
                    <AvatarImage
                      src="/"
                      alt="user"
                      width={6}
                      height={6}
                      className="object-contain"
                    />
                    <AvatarFallback>
                      {name && name.substring(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                </div>
              )}
              {message.role === "assistant" && (
                <div className="flex items-end gap-2">
                  <Avatar className="flex justify-start items-center">
                    <AvatarImage
                      src="/logo-black.svg"
                      alt="AI"
                      width={6}
                      height={6}
                      className="object-contain dark:invert"
                    />
                  </Avatar>
                  <div className="flex flex-col gap-2">
                    {/* Render reasoning annotations outside the bubble */}
                    {message.annotations && (
                      <div className="space-y-1">
                        <ReasoningAnnotation annotations={message.annotations} />
                        <ScreenshotAnnotation annotations={message.annotations} />
                      </div>
                    )}
                    
                    <div className="bg-accent p-3 rounded-md max-w-xs sm:max-w-2xl overflow-x-auto">
                      {/* Render tool invocations first */}
                      {message.toolInvocations && message.toolInvocations.length > 0 && (
                        <div className="mb-2">
                          {message.toolInvocations.map((invocation, index) => (
                            <ToolInvocation key={`${message.id}-tool-${index}`} invocation={invocation} />
                          ))}
                        </div>
                      )}
                      
                      {/* Render text content if present */}
                      {message.content && message.content.trim() && (
                        <div>
                          {/* Check if the message content contains a code block */}
                          {message.content.split("```").map((part, index) => {
                            if (index % 2 === 0) {
                              return (
                                <Markdown key={index} remarkPlugins={[remarkGfm]}>
                                  {part}
                                </Markdown>
                              );
                            } else {
                              return (
                                <pre className="whitespace-pre-wrap" key={index}>
                                  <CodeDisplayBlock code={part} />
                                </pre>
                              );
                            }
                          })}
                        </div>
                      )}
                      
                      {isLoading &&
                        messages.indexOf(message) === messages.length - 1 && (
                          <span className="animate-pulse" aria-label="Typing">
                            ...
                          </span>
                        )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        ))}
        {loadingSubmit && (
          <div className="flex pl-4 pb-4 gap-2 items-center">
            <Avatar className="flex justify-start items-center">
              <AvatarImage
                src="/logo-black.svg"
                alt="AI"
                width={6}
                height={6}
                className="object-contain dark:invert"
              />
            </Avatar>
            <div className="bg-accent p-3 rounded-md max-w-xs sm:max-w-2xl overflow-x-auto">
              <div className="flex gap-1">
                <span className="size-1.5 rounded-full bg-slate-700 motion-safe:animate-[bounce_1s_ease-in-out_infinite] dark:bg-slate-300"></span>
                <span className="size-1.5 rounded-full bg-slate-700 motion-safe:animate-[bounce_0.5s_ease-in-out_infinite] dark:bg-slate-300"></span>
                <span className="size-1.5 rounded-full bg-slate-700 motion-safe:animate-[bounce_1s_ease-in-out_infinite] dark:bg-slate-300"></span>
              </div>
            </div>
          </div>
        )}
      </div>
      <div id="anchor" ref={bottomRef}></div>
    </div>
  );
}
