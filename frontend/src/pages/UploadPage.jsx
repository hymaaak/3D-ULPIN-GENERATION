import { useState } from 'react';
import UploadPortal from '../components/UploadPortal.jsx';
import JobMonitor from '../components/JobMonitor.jsx';

export default function UploadPage() {
  // When a file's pipeline job is triggered, the monitor opens automatically
  // (spec section 10: "Post-upload: auto-trigger job selection").
  const [activeJobId, setActiveJobId] = useState(null);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <UploadPortal onJobCreated={setActiveJobId} />
      <JobMonitor jobId={activeJobId} onJobChange={setActiveJobId} />
    </div>
  );
}
