#!/bin/bash
# 验证 skill 目录结构完整性

echo "=== Skill 结构验证 ==="
errors=0
warnings=0

for skill_dir in skills/*/; do
    skill_name=$(basename "$skill_dir")
    
    # 检查 SKILL.md 是否存在
    if [ ! -f "$skill_dir/SKILL.md" ]; then
        echo "❌ $skill_name: 缺少 SKILL.md"
        ((errors++))
        continue
    fi
    
    # 检查 SKILL.md 是否有 frontmatter
    if ! head -1 "$skill_dir/SKILL.md" | grep -q "^---"; then
        echo "⚠️  $skill_name: SKILL.md 缺少 frontmatter"
        ((warnings++))
    fi
    
    # 检查 name 字段
    if ! grep -q "^name:" "$skill_dir/SKILL.md"; then
        echo "⚠️  $skill_name: SKILL.md 缺少 name 字段"
        ((warnings++))
    fi
    
    # 检查 description 字段
    if ! grep -q "^description:" "$skill_dir/SKILL.md"; then
        echo "⚠️  $skill_name: SKILL.md 缺少 description 字段"
        ((warnings++))
    fi
    
    # 检查引用的目录是否存在
    for subdir in scripts references assets hooks agents; do
        if grep -q "$subdir/" "$skill_dir/SKILL.md" 2>/dev/null; then
            if [ ! -d "$skill_dir/$subdir" ]; then
                echo "⚠️  $skill_name: SKILL.md 引用了 $subdir/ 但目录不存在"
                ((warnings++))
            fi
        fi
    done
done

echo ""
echo "=== 验证结果 ==="
echo "错误: $errors"
echo "警告: $warnings"
echo "检查的 skill 总数: $(ls -d skills/*/ | wc -l)"
