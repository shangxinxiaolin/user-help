package com.shangui.userhelp.logistics.domain;

import java.util.List;

public record LogisticsInfo(
        String trackingNo,
        String status,
        String currentCity,
        List<String> trace) {
}
