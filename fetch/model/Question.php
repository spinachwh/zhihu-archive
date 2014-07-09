<?php

namespace model;

class Question
{
    public static function getTable()
    {
        return get_table('question');
    }

    public static function saveQuestion($qid, $question, $descript)
    {
        $q = self::getTable();
        $update = array('title' => $question, 'description' => $descript);
        $where = array('id' => $qid, 'title' => $question, 'description' => $descript);
        $rs = $q->update($where, array('$set' => $update), array('upsert' => true));
        if (!$rs['ok']) {
            echo basename(__FILE__).':'.__LINE__.' '.$rs['err']."\n";
        }
        return $rs;
    }
    
    public static function getIds()
    {
        $c = self::getTable();
        $c = $c->find()->fields(array('id' => true));
        $ret = array();
        foreach ($c as $v) {
            $ret[] = $v['id'];
        }
        return $ret;
    }
}
