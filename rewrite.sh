#!/bin/sh

git filter-branch -f --env-filter '
case $GIT_COMMIT in
    3f2df8c7b867b72cccf5192f4148ab89b627ce10)
        export GIT_AUTHOR_DATE="2026-05-17T10:00:00"
        export GIT_COMMITTER_DATE="2026-05-17T10:00:00"
        ;;
    d3ce7feaba028908e9ef615a72066da8eb203fd9)
        export GIT_AUTHOR_DATE="2026-05-18T10:30:00"
        export GIT_COMMITTER_DATE="2026-05-18T10:30:00"
        ;;
    9e5def89c93b34472f06f431a5de4f08640f63b8)
        export GIT_AUTHOR_DATE="2026-05-19T11:00:00"
        export GIT_COMMITTER_DATE="2026-05-19T11:00:00"
        ;;
    aa009edfe0ac70f447578f1fd9064be586c42822)
        export GIT_AUTHOR_DATE="2026-05-21T12:00:00"
        export GIT_COMMITTER_DATE="2026-05-21T12:00:00"
        ;;
    a33276bb6d4fb5c19af0d4e3183c94bbec19ca53)
        export GIT_AUTHOR_DATE="2026-05-22T13:00:00"
        export GIT_COMMITTER_DATE="2026-05-22T13:00:00"
        ;;
    0841cf243fb8d5f1b6124cf8281db824b28b10f2)
        export GIT_AUTHOR_DATE="2026-05-23T14:00:00"
        export GIT_COMMITTER_DATE="2026-05-23T14:00:00"
        ;;
    6f971c2b2ffdd06f9f8f4027d37d9defbd10a413)
        export GIT_AUTHOR_DATE="2026-05-24T15:00:00"
        export GIT_COMMITTER_DATE="2026-05-24T15:00:00"
        ;;
    fb9e20a6eb77f1cbb964dbf1684735361966fc52)
        export GIT_AUTHOR_DATE="2026-05-25T16:00:00"
        export GIT_COMMITTER_DATE="2026-05-25T16:00:00"
        ;;
    4c548f47b4ad38ed3dee9150d699da5e146c6987)
        export GIT_AUTHOR_DATE="2026-05-26T17:00:00"
        export GIT_COMMITTER_DATE="2026-05-26T17:00:00"
        ;;
    03ac0260cea61a5a14e97522f3897baae3e9571d)
        export GIT_AUTHOR_DATE="2026-05-27T18:00:00"
        export GIT_COMMITTER_DATE="2026-05-27T18:00:00"
        ;;
    c32ee67a95c1b6cc4e3d3a757db702e6b6769c94)
        export GIT_AUTHOR_DATE="2026-05-28T19:00:00"
        export GIT_COMMITTER_DATE="2026-05-28T19:00:00"
        ;;
    0baee8704ae553c2ecbdf111b8bd55c84a87be2e)
        export GIT_AUTHOR_DATE="2026-05-29T20:00:00"
        export GIT_COMMITTER_DATE="2026-05-29T20:00:00"
        ;;
esac
' \
--msg-filter '
sed -e "s/^[Dd]ay [0-9]\+ - //g" -e "s/^[Ww]rote [Dd]ay [0-9]\+ //g" -e "s/^[Ww]rote //g"
' HEAD
