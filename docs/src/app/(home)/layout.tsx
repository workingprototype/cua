import { DocsLayout } from 'fumadocs-ui/layouts/docs';
import type { ReactNode } from 'react';
import { baseOptions } from '@/app/layout.config';
import { source } from '@/lib/source';
import { CodeXml } from 'lucide-react';

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <DocsLayout
      tree={source.pageTree}
      sidebar={{
        tabs: [
          {
            url: '/v1',
            title: 'API v1',
            icon: (
              <div
                className="rounded-lg bg-blue-500/10 border max-md:p-1.5 p-1"
                style={
                  {
                    color: 'var(--color-blue-500)',
                  } as object
                }>
                <CodeXml />
              </div>
            ),
          },
        ],
      }}
      {...baseOptions}>
      {children}
    </DocsLayout>
  );
}
