#!/usr/bin/env bash
# xls-poi skill 环境：Java 8 + POI 4.1.2（路径已固化，正斜杠避免 Git Bash 转义问题）
# 用法: source poi_env.sh 后调用 poi_compile / poi_run；或 bash poi_env.sh <MainClass> <args...>
POI_CP="D:/develop/apache-maven-3.6.3/mvn_repo/org/apache/poi/poi/4.1.2/poi-4.1.2.jar;D:/develop/apache-maven-3.6.3/mvn_repo/org/apache/poi/poi-ooxml/4.1.2/poi-ooxml-4.1.2.jar;D:/develop/apache-maven-3.6.3/mvn_repo/org/apache/poi/poi-ooxml-schemas/4.1.2/poi-ooxml-schemas-4.1.2.jar;D:/develop/apache-maven-3.6.3/mvn_repo/org/apache/xmlbeans/xmlbeans/3.1.0/xmlbeans-3.1.0.jar;D:/develop/apache-maven-3.6.3/mvn_repo/org/apache/commons/commons-compress/1.19/commons-compress-1.19.jar;D:/develop/apache-maven-3.6.3/mvn_repo/com/github/virtuald/curvesapi/1.04/curvesapi-1.04.jar;D:/develop/apache-maven-3.6.3/mvn_repo/org/apache/commons/commons-math3/3.6.1/commons-math3-3.6.1.jar;D:/develop/apache-maven-3.6.3/mvn_repo/commons-codec/commons-codec/1.13/commons-codec-1.13.jar;D:/develop/apache-maven-3.6.3/mvn_repo/org/apache/commons/commons-collections4/4.4/commons-collections4-4.4.jar;D:/develop/apache-maven-3.6.3/mvn_repo/commons-logging/commons-logging/1.2/commons-logging-1.2.jar"

poi_compile() {
  javac -encoding UTF-8 -cp "$POI_CP" "$@"
}

poi_run() {
  local main="$1"
  shift
  java -Dfile.encoding=UTF-8 -cp "$POI_CP;." "$main" "$@"
}

if [ "$0" != "bash" ] && [ "${BASH_SOURCE[0]}" != "$0" ]; then
  # sourced
  return 0 2>/dev/null
fi

if [ $# -ge 1 ]; then
  poi_run "$@"
fi
