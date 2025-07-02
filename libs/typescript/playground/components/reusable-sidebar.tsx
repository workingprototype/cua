"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { Button, buttonVariants } from "@/components/ui/button";
import Link from "next/link";

interface SidebarButton {
  id: string;
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
}

interface SidebarLink {
  id: string;
  label: string;
  href?: string;
  isActive?: boolean;
  onClick?: () => void;
  icon?: React.ReactNode;
}

interface ReusableSidebarProps {
  buttons?: SidebarButton[];
  links: SidebarLink[];
  linksTitle?: string;
  className?: string;
}

export function ReusableSidebar({
  buttons = [],
  links,
  linksTitle,
  className
}: ReusableSidebarProps) {
  return (
    <div className={cn(
      "relative justify-between group lg:bg-accent/20 lg:dark:bg-card/35 flex flex-col h-full gap-4 p-2",
      className
    )}>
      <div className="flex flex-col justify-between p-2 max-h-fit overflow-y-auto">
        {/* Action Buttons */}
        {buttons.length > 0 && (
          <div className="space-y-2 mb-4">
            {buttons.map((button) => (
              <Button
                key={button.id}
                onClick={button.onClick}
                variant="ghost"
                className="flex justify-between w-full h-14 text-sm xl:text-lg font-normal items-center"
              >
                <div className="flex gap-3 items-center">
                  {button.label}
                </div>
                {button.icon}
              </Button>
            ))}
          </div>
        )}

        {/* Links Section */}
        <div className="flex flex-col pt-4 gap-2">
          {linksTitle && (
            <p className="pl-4 text-xs text-muted-foreground">{linksTitle}</p>
          )}
          {links.length > 0 ? (
            <div className="space-y-1">
              {links.map((link) => {
                const content = (
                  <div className="flex gap-3 items-center truncate">
                    {link.icon && (
                      <div className="flex-shrink-0">
                        {link.icon}
                      </div>
                    )}
                    <div className="flex flex-col">
                      <span className="text-xs font-normal">
                        {link.label}
                      </span>
                    </div>
                  </div>
                );

                if (link.href) {
                  return (
                    <Link
                      key={link.id}
                      href={link.href}
                      className={cn(
                        {
                          [buttonVariants({ variant: "secondaryLink" })]: link.isActive,
                          [buttonVariants({ variant: "ghost" })]: !link.isActive,
                        },
                        "flex justify-between w-full h-14 text-base font-normal items-center"
                      )}
                    >
                      {content}
                    </Link>
                  );
                } else {
                  return (
                    <Button
                      key={link.id}
                      onClick={link.onClick}
                      variant={link.isActive ? "secondaryLink" : "ghost"}
                      className="flex justify-between w-full h-14 text-base font-normal items-center"
                    >
                      {content}
                    </Button>
                  );
                }
              })}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <p className="text-sm">No items yet</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
