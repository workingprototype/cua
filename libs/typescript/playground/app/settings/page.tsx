"use client";

import React, { useState } from "react";
import { ReusableSidebar } from "@/components/reusable-sidebar";
import { GeneralSettings } from "@/components/settings/general-settings";
import { ApiKeysSettings } from "@/components/settings/api-keys-settings";
import { ComputersSettings } from "@/components/settings/computers-settings";

export default function SettingsPage() {
  const [activeSection, setActiveSection] = useState("general");

  const settingsLinks = [
    {
      id: "general",
      label: "General",
      isActive: activeSection === "general",
      onClick: () => setActiveSection("general")
    },
    {
      id: "api-keys",
      label: "API Keys",
      isActive: activeSection === "api-keys",
      onClick: () => setActiveSection("api-keys")
    },
    {
      id: "computers",
      label: "Computers",
      isActive: activeSection === "computers",
      onClick: () => setActiveSection("computers")
    }
  ];

  const renderContent = () => {
    switch (activeSection) {
      case "general":
        return <GeneralSettings />;
      case "api-keys":
        return <ApiKeysSettings />;
      case "computers":
        return <ComputersSettings />;
      default:
        return <GeneralSettings />;
    }
  };

  return (
    <div className="h-screen bg-background">
      <div className="flex h-full">
        <div className="w-64">
          <ReusableSidebar
            links={settingsLinks}
            linksTitle="Settings"
          />
        </div>
        <div className="flex-1 overflow-auto">
          {renderContent()}
        </div>
      </div>
    </div>
  );
}
