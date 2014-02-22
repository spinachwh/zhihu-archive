<?php

function save_answer($base_url, $username, $answer_link_list) {
    foreach ($answer_link_list as $url) {
        $url = $base_url.$url;
        list($_, $content) = odie_get($url);
        list($question, $content) = parse_answer($content);
        echo "\t$question\n";
        $content = '<link rel="stylesheet" href="http://static.zhihu.com/static/ver/f004e446ca569e4897e59cf26da3e2dc.z.css" type="text/css" media="screen,print" />'
            .$content
            .'<div><a href="'.$url.'">原链接</a></div>'
            .'<script src="http://code.jquery.com/jquery-1.11.0.min.js"></script>'
            .'<script>$("img").each(function(){$(this).attr("src",$(this).attr("data-actualsrc"))});</script>'
            ;
        $root = __DIR__."/$username";
        if (!is_dir($root)) {
            mkdir($root);
        }
        file_put_contents("$root/$question.html", $content);
    }
}

function parse_answer($content) {
    $dom = HTML5::loadHTML($content);
    $answer = $dom->getElementById('zh-question-answer-wrap');
    $answer = ($answer->C14N());
    $q = $dom->getElementById('zh-question-title');
    $a = $q->getElementsByTagName('a')->item(0);
    $question = $a->textContent;
    return array($question, $answer);
}

function get_answer_link_list($content) {
    $dom = HTML5::loadHTML($content);
    $dom = $dom->getElementById('zh-profile-answer-list');
    $ret = array();
    foreach ($dom->getElementsByTagName('a') as $key => $node) {
        if ($attr = $node->getAttribute('class') == 'question_link') {
            $ret[] = ($node->getAttribute('href'));
        }
    }
    return $ret;
}

function get_page_num($content) {
    $rs = preg_match_all('%<a href="\?page=(\d+)%', $content, $matches);
    if (!$rs) {
        throw new Exception("num match fail", 1);
    }
    return (int) max($matches[1]);
}

function get_username_list($content) {
    $dom = HTML5::loadHTML($content);
    foreach ($dom->getElementsByTagName('a') as $key => $node) {
        $href = $node->getAttribute('href');
        if (preg_match('%/people/(.+)$%', $href, $matches)) {
            $username = $matches[1];
            $ret[$username] = $node->textContent;
        }
    }
    return ($ret);
}
