import { DocsLayout } from 'fumadocs-ui/layouts/docs';
import type { ReactNode } from 'react';
import { baseOptions } from '@/app/layout.config';
import { source } from '@/lib/source';
import { Home, Library, Cloud } from 'lucide-react';

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <DocsLayout
      tree={source.pageTree}
      sidebar={{
        tabs: [
          {
            url: '/home',
            title: 'Home',
            description: 'Welcome to Cua Documentation',
            icon: <Home />,
          },
          {
            url: '/libraries',
            title: 'Libraries',
            description: 'Library Documentation',
            icon: <Library />,
          },
          {
            url: '/cloud',
            title: 'Cloud',
            description: 'Cua Cloud Documentation',
            icon: <Cloud />,
          },
        ],
      }}
      {...baseOptions}
    >
      {children}
    </DocsLayout>
  );
}
