import React, { useState } from "react";
import { FiInfo, FiCheck, FiX, FiHelpCircle } from "react-icons/fi";

export default function PairwiseMatrixView({
  rankings = [],
  matrix = [],
  schemeIds = [],
  pairwiseDetails = [],
}) {
  const [selectedPair, setSelectedPair] = useState(null);

  if (!matrix || matrix.length === 0 || !rankings || rankings.length === 0) {
    return null;
  }

  const idToTitle = {};
  rankings.forEach((r) => {
    idToTitle[r.scheme_id] = r.title;
  });

  const handleCellClick = (i, j) => {
    if (i === j) return;
    const idA = schemeIds[i];
    const idB = schemeIds[j];

    // Find corresponding pairwise detail
    const detail = pairwiseDetails.find(
      (p) =>
        (p.scheme_a_id === idA && p.scheme_b_id === idB) ||
        (p.scheme_a_id === idB && p.scheme_b_id === idA)
    );

    setSelectedPair({
      rowIdx: i,
      colIdx: j,
      idA,
      idB,
      titleA: idToTitle[idA] || `Scheme ${i + 1}`,
      titleB: idToTitle[idB] || `Scheme ${j + 1}`,
      prob: matrix[i][j],
      detail,
    });
  };

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="mb-4">
        <h3 className="text-base font-bold text-navy-900 flex items-center gap-2">
          <span>Head-to-Head Pairwise Win-Rate Matrix</span>
          <span className="rounded bg-indigo-50 px-2 py-0.5 text-xs font-semibold text-indigo-700">
            K × K Tournament
          </span>
        </h3>
        <p className="text-xs text-slate-500 mt-1">
          Cell [Row, Column] indicates the model's preference probability that the <strong>Row Scheme</strong> is more advantageous for your MSME than the <strong>Column Scheme</strong>. Click any cell to view the exact comparison rationale.
        </p>
      </div>

      {/* Matrix Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-center text-xs border-collapse">
          <thead>
            <tr>
              <th className="p-2 text-left font-semibold text-slate-400 bg-slate-50 border border-slate-200">
                Row vs Col
              </th>
              {schemeIds.map((id, idx) => (
                <th
                  key={id}
                  className="p-2 font-semibold text-slate-700 bg-slate-50 border border-slate-200 max-w-[120px] truncate"
                  title={idToTitle[id]}
                >
                  #{idx + 1}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, i) => (
              <tr key={schemeIds[i] || i}>
                <td
                  className="p-2 text-left font-medium text-slate-800 bg-slate-50 border border-slate-200 max-w-[180px] truncate"
                  title={idToTitle[schemeIds[i]]}
                >
                  <span className="font-bold text-navy-900 mr-1.5">#{i + 1}</span>
                  {idToTitle[schemeIds[i]] || `Scheme ${i + 1}`}
                </td>
                {row.map((val, j) => {
                  if (i === j) {
                    return (
                      <td
                        key={j}
                        className="p-2 text-slate-300 bg-slate-100/50 border border-slate-200 font-mono"
                      >
                        —
                      </td>
                    );
                  }

                  const isWinner = val > 0.5;
                  const isStrong = val >= 0.75;
                  const isSelected =
                    selectedPair &&
                    selectedPair.rowIdx === i &&
                    selectedPair.colIdx === j;

                  let cellBg = "bg-slate-50 hover:bg-slate-100 text-slate-600";
                  if (val > 0.55) {
                    cellBg = isStrong
                      ? "bg-emerald-100/80 hover:bg-emerald-200 text-emerald-900 font-semibold"
                      : "bg-emerald-50 hover:bg-emerald-100 text-emerald-800";
                  } else if (val < 0.45) {
                    cellBg = val <= 0.25
                      ? "bg-rose-100/70 hover:bg-rose-200 text-rose-900"
                      : "bg-rose-50 hover:bg-rose-100 text-rose-700";
                  }

                  return (
                    <td
                      key={j}
                      onClick={() => handleCellClick(i, j)}
                      className={`p-2 border border-slate-200 cursor-pointer font-mono text-xs transition select-none ${cellBg} ${
                        isSelected ? "ring-2 ring-indigo-500 z-10" : ""
                      }`}
                      title={`Click to inspect #${i + 1} vs #${j + 1}`}
                    >
                      {(val * 100).toFixed(0)}%
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Interactive Pairwise Inspection Drawer */}
      {selectedPair && (
        <div className="mt-4 rounded-lg border border-indigo-200 bg-indigo-50/50 p-4 transition">
          <div className="flex items-start justify-between gap-3">
            <div>
              <span className="inline-flex items-center gap-1 text-xs font-bold uppercase tracking-wider text-indigo-700">
                <FiInfo size={13} /> Pairwise Inspection Rationale
              </span>
              <h4 className="mt-1 text-sm font-bold text-navy-900">
                {selectedPair.titleA} <span className="text-slate-400 font-normal">vs</span> {selectedPair.titleB}
              </h4>
            </div>
            <button
              onClick={() => setSelectedPair(null)}
              className="text-slate-400 hover:text-slate-600 p-1"
            >
              <FiX size={16} />
            </button>
          </div>

          <div className="mt-2 text-xs text-slate-700 leading-relaxed bg-white p-3 rounded border border-indigo-100 shadow-2xs">
            <p className="font-semibold text-navy-900 mb-1">
              Win Probability: {(selectedPair.prob * 100).toFixed(1)}% preference for {selectedPair.titleA}
            </p>
            <p>
              {selectedPair.detail?.comparative_rationale ||
                `${selectedPair.titleA} was compared against ${selectedPair.titleB} based on your enterprise classification and activity.`}
            </p>

            {selectedPair.detail?.driving_attributes && selectedPair.detail.driving_attributes.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1.5 items-center">
                <span className="text-slate-400 font-medium">Deciding attributes:</span>
                {selectedPair.detail.driving_attributes.map((attr) => (
                  <span
                    key={attr}
                    className="rounded bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-800"
                  >
                    {attr}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
