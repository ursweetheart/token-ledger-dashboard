"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");

const appSource = fs.readFileSync(path.join(__dirname, "..", "web", "js", "app.js"), "utf8");

/* Trích đúng hàm cần đo, không nạp cả app.js: hàm này thuần tính toán, không
   chạm DOM, nên đo được tách biệt. */
function loadOutliers(groups) {
  const src = appSource.match(/var AGENT_COST_OUTLIER_RATIO[\s\S]*?\n\}/);
  assert.ok(src, "agentCostOutliers phải tồn tại");
  const sandbox = {
    console,
    // groupAgg giả: trả thẳng nhóm đã dựng sẵn, vì ta đang đo LOGIC NGƯỠNG
    // chứ không đo lại phép gộp.
    groupAgg: () => groups
  };
  vm.createContext(sandbox);
  vm.runInContext(src[0], sandbox);
  return sandbox.agentCostOutliers([]);
}

test("chỉ agent có CẢ chi phí lẫn request mới vào mẫu", () => {
  const o = loadOutliers([
    { key: "A", cost: 10, r: 100 },
    { key: "B", cost: 0, r: 50 },    // có request, chưa quy được tiền
    { key: "C", cost: 5, r: 0 }      // có tiền, không request trong kỳ
  ]);
  assert.equal(o.sample, 1, "B và C phải bị loại khỏi mẫu");
  assert.equal(o.avg, 10);
});

test("ngưỡng là VƯỢT 30%, không phải đạt 30%", () => {
  // avg = 100. Agent đúng 130 là KHÔNG vượt; 130.01 mới vượt.
  const bang = loadOutliers([
    { key: "A", cost: 130, r: 1 }, { key: "B", cost: 85, r: 1 }, { key: "C", cost: 85, r: 1 }
  ]);
  assert.equal(bang.avg, 100);
  assert.equal(bang.flagged.length, 0, "đúng 1,30 lần thì chưa cảnh báo");

  const vuot = loadOutliers([
    { key: "A", cost: 130.5, r: 1 }, { key: "B", cost: 85, r: 1 }, { key: "C", cost: 84.5, r: 1 }
  ]);
  assert.equal(vuot.flagged.length, 1);
  assert.equal(vuot.flagged[0].key, "A");
});

test("mẫu nhỏ bị đánh dấu, không bị giấu đi", () => {
  const o = loadOutliers([{ key: "A", cost: 100, r: 1 }, { key: "B", cost: 1, r: 1 }]);
  assert.equal(o.small, true, "2 agent phải bị đánh dấu là mẫu nhỏ");
  // Vẫn tính, vẫn cảnh báo — chỉ kèm lời nhắc.
  assert.equal(o.flagged.length, 1);
});

test("không agent nào hoạt động thì không chia cho 0", () => {
  const o = loadOutliers([]);
  assert.equal(o.sample, 0);
  assert.equal(o.avg, 0);
  assert.equal(o.flagged.length, 0);
});

test("kết quả xếp theo chi phí giảm dần", () => {
  // total 920 / 4 = 230; ngưỡng 299. Cả 500 lẫn 400 đều vượt.
  const o = loadOutliers([
    { key: "nhi", cost: 400, r: 1 }, { key: "nhat", cost: 500, r: 1 },
    { key: "beo", cost: 10, r: 1 }, { key: "teo", cost: 10, r: 1 }
  ]);
  assert.deepEqual(o.flagged.map((g) => g.key), ["nhat", "nhi"]);
});

/* TÍNH CHẤT CỦA CHÍNH PHÉP ĐO, không phải lỗi: một agent quá lớn tự kéo mức
   trung bình lên và che mất agent lớn vừa. [200, 900, 10, 10] cho trung bình
   280, ngưỡng 364 — nên 200 KHÔNG bị cảnh báo dù nó gấp 20 lần hai agent nhỏ.
   Ghim lại để lần sau ai đọc con số cũng biết đây là hành vi đã lường trước,
   và để nếu có ai đổi công thức thì phép kiểm này gãy chứ không im. */
test("một agent quá lớn kéo trung bình lên và che agent lớn vừa", () => {
  const o = loadOutliers([
    { key: "nho", cost: 200, r: 1 }, { key: "lon", cost: 900, r: 1 },
    { key: "beo", cost: 10, r: 1 }, { key: "teo", cost: 10, r: 1 }
  ]);
  assert.equal(o.avg, 280);
  assert.deepEqual(o.flagged.map((g) => g.key), ["lon"]);
});
