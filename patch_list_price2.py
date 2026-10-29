p = "app/models.py"
s = open(p).read()
old = 'SELECT mrp_inr FROM products WHERE sku IN (:a, :b) AND mrp_inr IS NOT NULL LIMIT 1'
new = 'SELECT COALESCE(mrp_inr, mrp_gst) FROM products WHERE sku IN (:a, :b) AND COALESCE(mrp_inr, mrp_gst) IS NOT NULL LIMIT 1'
assert s.count(old) == 1, s.count(old)
open(p, "w").write(s.replace(old, new)); print("patched")
