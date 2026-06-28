import { useState } from "react";

import AskPanel from "./components/AskPanel/AskPanel";
import DataTable from "./components/DataTable/DataTable";
import FileUpload from "./components/FileUpload/FileUpload";

/**
 * Top-level layout. Holds the `activeDataset` (the most recently uploaded
 * dataset). The DataTable browses its rows; the AskPanel answers questions.
 *
 * State flow:
 *   FileUpload --(onUploaded)--> activeDataset --(prop)--> DataTable & AskPanel
 *   DataTable owns rows/pagination/search/sort/filter state via useRows.
 *   AskPanel owns the ask request state via useAsk.
 */
export default function App() {
  const [activeDataset, setActiveDataset] = useState(null);

  return (
    <div className="app">
      <header className="app__header">
        <h1>Dataset Explorer with AI Insights</h1>
        <p className="app__subtitle">
          Transform raw data into instant insights. Upload a dataset and chat with your AI analyst in
          plain English.
        </p>
      </header>

      <main className="app__main">
        <FileUpload onUploaded={setActiveDataset} />

        {activeDataset && <DataTable dataset={activeDataset} />}

        {activeDataset && <AskPanel dataset={activeDataset} />}
      </main>

    </div>
  );
}
