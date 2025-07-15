"use client";

import React, { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";
import { useComputerStore, ComputerInstance } from "../../app/hooks/useComputerStore";
import { Monitor, Save, RotateCcw } from "lucide-react";
import yaml from "js-yaml";

export function ComputersSettings() {
  const { instances, setInstances, resetToDefault } = useComputerStore();
  const [yamlContent, setYamlContent] = useState("");
  const [isValid, setIsValid] = useState(true);

  // Convert instances to YAML format
  const instancesToYaml = (instances: ComputerInstance[]) => {
    const yamlData = instances.map(instance => ({
      provider: instance.provider,
      name: instance.name,
      os: instance.os,
      password: instance.password
    }));
    
    return yaml.dump({ computers: yamlData }, { 
      indent: 2,
      lineWidth: -1,
      noRefs: true
    });
  };

  // Convert YAML to instances
  const yamlToInstances = (yamlContent: string): ComputerInstance[] => {
    try {
      const parsed = yaml.load(yamlContent) as { computers: any[] };
      
      if (!parsed || !parsed.computers || !Array.isArray(parsed.computers)) {
        throw new Error("Invalid YAML structure. Expected 'computers' array.");
      }

      return parsed.computers.map((comp, index) => ({
        id: (index + 1).toString(),
        name: comp.name || `Computer ${index + 1}`,
        status: "stopped",
        type: "medium",
        provider: comp.provider || "lume",
        os: comp.os || "ubuntu",
        password: comp.password
      }));
    } catch (error) {
      throw new Error(`YAML parsing error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  // Load current instances into YAML on component mount
  useEffect(() => {
    const currentYaml = instancesToYaml(instances);
    setYamlContent(currentYaml);
  }, [instances]);

  // Validate YAML as user types
  const handleYamlChange = (value: string) => {
    setYamlContent(value);
    
    try {
      yamlToInstances(value);
      setIsValid(true);
    } catch (error) {
      setIsValid(false);
    }
  };

  // Save YAML to store
  const handleSave = () => {
    try {
      const newInstances = yamlToInstances(yamlContent);
      setInstances(newInstances);
      setIsValid(true);
      toast.success("Computer configuration saved successfully!");
    } catch (error) {
      toast.error(`Failed to save: ${error instanceof Error ? error.message : 'Unknown error'}`);
      setIsValid(false);
    }
  };

  // Reset to default configuration
  const handleReset = () => {
    resetToDefault();
    setIsValid(true);
    toast.info("Reset to default configuration");
  };

  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div>
        <h2 className="text-xl font-semibold mb-2">Computer Configuration</h2>
        <p className="text-muted-foreground">
          Configure your computer instances using YAML. Changes will be reflected in the computers tab and chat dropdown.
        </p>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Monitor className="h-5 w-5" />
            Computer Instances (YAML)
          </CardTitle>
          <CardDescription>
            Define your computer instances in YAML format. Each computer should have a provider, name, and os.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <label className="text-sm font-medium">YAML Configuration</label>
              <div className="flex gap-2">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleReset}
                  className="flex items-center gap-1"
                >
                  <RotateCcw className="h-4 w-4" />
                  Reset to Default
                </Button>
                <Button
                  type="button"
                  onClick={handleSave}
                  disabled={!isValid}
                  className="flex items-center gap-1"
                >
                  <Save className="h-4 w-4" />
                  Save Configuration
                </Button>
              </div>
            </div>
            
            <Textarea
              value={yamlContent}
              onChange={(e) => handleYamlChange(e.target.value)}
              placeholder="computers:
  - provider: lume
    name: macos-sequoia-cua:latest
    os: macos-sequoia
  - provider: windows-sandbox
    name: Windows Sandbox
    os: windows"
              className={`font-mono text-sm min-h-[400px] ${
                !isValid ? 'border-destructive' : ''
              }`}
            />
            
            {!isValid && (
              <p className="text-sm text-destructive">
                Invalid YAML format. Please check your syntax.
              </p>
            )}
          </div>

          <div className="bg-muted/50 p-4 rounded-lg">
            <h4 className="font-medium mb-2">Supported Fields:</h4>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li><code className="bg-muted px-1 rounded">provider</code> - lume, windows-sandbox, cua-cloud</li>
              <li><code className="bg-muted px-1 rounded">name</code> - Display name for the computer</li>
              <li><code className="bg-muted px-1 rounded">os</code> - ubuntu, macos-sequoia, windows, etc.</li>
              <li><code className="bg-muted px-1 rounded">password</code> - Password for the noVNC</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
